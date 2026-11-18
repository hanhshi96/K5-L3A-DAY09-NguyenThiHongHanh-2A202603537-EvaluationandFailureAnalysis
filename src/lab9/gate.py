
"""CI gate for Lab 09 evaluation.

M5: slice-level regression checks.
M7: report integrity and threshold ratchet.

exit 0 = merge
exit 1 = blocked
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from numbers import Real
from typing import Any

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item

from lab9.graders import GRADERS


def _finite_number(value: Any) -> bool:
    """Return True when value is a finite real number."""
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _row_key(row: dict) -> tuple | None:
    """Stable identity of one evaluation trial."""
    item_id = row.get("item_id")
    seed = row.get("seed")

    if item_id is None or seed is None:
        return None

    try:
        hash((item_id, seed))
    except TypeError:
        return None

    return item_id, seed


def _slice_tags(row: dict) -> tuple[str, ...]:
    """Normalize slice tags for reliable comparison."""
    tags = row.get("slices") or []

    if isinstance(tags, str):
        tags = [tags]

    if not isinstance(tags, (list, tuple, set)):
        return ()

    return tuple(sorted(str(tag) for tag in tags))


def _index_rows(report: dict, label: str, problems: list[str]) -> dict:
    """Index rows and detect malformed or duplicated item-seed pairs."""
    rows = report.get("rows")

    if not isinstance(rows, list):
        problems.append(f"{label}: rows must be a list")
        return {}

    indexed = {}

    for row in rows:
        if not isinstance(row, dict):
            problems.append(f"{label}: malformed row")
            continue

        key = _row_key(row)

        if key is None:
            problems.append(f"{label}: row missing valid item_id or seed")
            continue

        if key in indexed:
            problems.append(f"{label}: duplicate item-seed pair {key}")
            continue

        indexed[key] = row

    return indexed


def _check_ratchet(
    spec: dict,
    base_spec: dict,
    problems: list[str],
) -> None:
    """Prevent thresholds and blocking requirements from becoming weaker."""

    # Only compare thresholds within the same evaluation-set version.
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return

    current_metrics = {
        m.get("id"): m
        for m in spec.get("metrics", [])
        if isinstance(m, dict) and m.get("id")
    }

    previous_metrics = {
        m.get("id"): m
        for m in base_spec.get("metrics", [])
        if isinstance(m, dict) and m.get("id")
    }

    for mid, old in previous_metrics.items():
        new = current_metrics.get(mid)

        if new is None:
            problems.append(f"ratchet: metric {mid} disappeared")
            continue

        old_th = old.get("threshold") or {}
        new_th = new.get("threshold") or {}

        for key in ("max", "max_increase"):
            if key in old_th:
                if key not in new_th:
                    problems.append(
                        f"ratchet: metric {mid} removed threshold {key}"
                    )
                elif (
                    not _finite_number(new_th[key])
                    or new_th[key] > old_th[key]
                ):
                    problems.append(
                        f"ratchet: metric {mid} loosened {key}"
                    )

        for key in ("min",):
            if key in old_th:
                if key not in new_th:
                    problems.append(
                        f"ratchet: metric {mid} removed threshold {key}"
                    )
                elif (
                    not _finite_number(new_th[key])
                    or new_th[key] < old_th[key]
                ):
                    problems.append(
                        f"ratchet: metric {mid} loosened {key}"
                    )

        if old_th.get("no_significant_drop") and not new_th.get(
            "no_significant_drop"
        ):
            problems.append(
                f"ratchet: metric {mid} removed no_significant_drop"
            )

        if old.get("blocking") and not new.get("blocking"):
            problems.append(
                f"ratchet: metric {mid} changed from blocking to non-blocking"
            )

    # Apply the same rules to slices.
    current_slices = {
        s.get("name"): s
        for s in spec.get("slices", [])
        if isinstance(s, dict) and s.get("name")
    }

    previous_slices = {
        s.get("name"): s
        for s in base_spec.get("slices", [])
        if isinstance(s, dict) and s.get("name")
    }

    for name, old in previous_slices.items():
        new = current_slices.get(name)

        if new is None:
            problems.append(f"ratchet: slice {name} disappeared")
            continue

        if old.get("metric") != new.get("metric"):
            problems.append(
                f"ratchet: slice {name} changed its metric"
            )

        for key in ("min",):
            if key in old:
                if key not in new:
                    problems.append(
                        f"ratchet: slice {name} removed threshold {key}"
                    )
                elif (
                    not _finite_number(new[key])
                    or new[key] < old[key]
                ):
                    problems.append(
                        f"ratchet: slice {name} loosened {key}"
                    )

        for key in ("max",):
            if key in old:
                if key not in new:
                    problems.append(
                        f"ratchet: slice {name} removed threshold {key}"
                    )
                elif (
                    not _finite_number(new[key])
                    or new[key] > old[key]
                ):
                    problems.append(
                        f"ratchet: slice {name} loosened {key}"
                    )

        if old.get("no_significant_drop") and not new.get(
            "no_significant_drop"
        ):
            problems.append(
                f"ratchet: slice {name} removed no_significant_drop"
            )

        if old.get("blocking") and not new.get("blocking"):
            problems.append(
                f"ratchet: slice {name} changed from blocking to non-blocking"
            )


def integrity_check(
    pr: dict,
    base: dict,
    spec: dict,
    base_spec: dict | None = None,
) -> list[str]:
    """M7: validate report integrity and enforce the threshold ratchet."""

    problems: list[str] = []

    if not isinstance(pr.get("metrics"), dict):
        problems.append("PR metrics must be a dictionary")

    if not isinstance(base.get("metrics"), dict):
        problems.append("baseline metrics must be a dictionary")

    # 1. Reject NaN and infinity in aggregate PR metrics.
    for mid, value in (pr.get("metrics") or {}).items():
        if isinstance(value, Real) and not _finite_number(value):
            problems.append(f"PR metric {mid} is NaN or infinite")

    # 2. Check manifest and expected row count.
    manifest = pr.get("manifest") or {}
    rows = pr.get("rows")

    if not isinstance(rows, list):
        problems.append("PR rows must be a list")
        rows = []

    items = manifest.get("items")
    seeds = manifest.get("seeds")

    if (
        isinstance(items, int)
        and not isinstance(items, bool)
        and items >= 0
        and isinstance(seeds, list)
    ):
        if len(set(seeds)) != len(seeds):
            problems.append("PR manifest contains duplicate seeds")

        expected = items * len(seeds)

        if len(rows) != expected:
            problems.append(
                f"PR row count {len(rows)} != expected {expected}"
            )
    else:
        problems.append("PR manifest has invalid items or seeds")

    # 3. Detect missing evaluator results.
    failures = pr.get("evaluator_failures") or []

    if failures:
        problems.append(
            f"PR has {len(failures)} evaluator failure(s)"
        )

    # Only row-level metrics are required on every trial.
    row_metric_ids = [
    metric["id"] for metric in spec["metrics"]
    if metric["id"] in GRADERS
    ]

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue  # _index_rows bên dưới sẽ ghi lỗi "malformed row"
        for metric_id in row_metric_ids:
            value = row.get(metric_id)
            if value is None:
                problems.append(f"PR row {index} has missing graded metric {metric_id}")
            elif not isinstance(value, bool):
                problems.append(f"PR row {index} has invalid grader result {metric_id}")

    # 4. Check item-seed uniqueness and compare with baseline.
    pr_rows = _index_rows(pr, "PR", problems)
    base_rows = _index_rows(base, "baseline", problems)

    if set(pr_rows) != set(base_rows):
        problems.append(
            "PR item-seed pairs differ from baseline"
        )

    # 5. Slice labels must not be changed between PR and baseline.
    for key in set(pr_rows) & set(base_rows):
        pr_tags = _slice_tags(pr_rows[key])
        base_tags = _slice_tags(base_rows[key])

        if pr_tags != base_tags:
            problems.append(
                f"slice tags changed for item-seed {key}"
            )

    # 6. Enforce the ratchet against main's metric specification.
    if base_spec is not None:
        _check_ratchet(spec, base_spec, problems)

    return sorted(set(problems))


def slice_check(
    pr: dict,
    base: dict,
    spec: dict,
) -> tuple[list[str], list[str]]:
    """M5: evaluate every configured slice independently."""

    blocked: list[str] = []
    lines: list[str] = []

    bootstrap_cfg = spec.get("bootstrap", {})
    n_resamples = bootstrap_cfg.get("n_resamples", 1000)
    rng = bootstrap_cfg.get("rng", 2027)
    confidence = bootstrap_cfg.get("confidence", 0.95)

    for entry in spec.get("slices", []):
        name = entry["name"]
        metric = entry["metric"]
        blocking = entry.get("blocking", False)

        slice_id = f"slice:{name}/{metric}"

        pr_items = per_item(pr, metric, slice_name=name)
        base_items = per_item(base, metric, slice_name=name)

        if not pr_items:
            verdict = "MISSING"
            lines.append(
                f"  {slice_id:<35} no PR items available"
            )

            if blocking:
                blocked.append(slice_id)

            continue

        value = sum(pr_items.values()) / len(pr_items)

        notes = []
        failed = False

        # Absolute performance floor.
        minimum = entry.get("min")

        if minimum is not None and value < minimum:
            failed = True
            notes.append(
                f"value {value:.3f} < min {minimum:.3f}"
            )

        # Paired confidence interval against baseline.
        if entry.get("no_significant_drop"):
            keys = sorted(set(pr_items) & set(base_items))

            if not keys:
                failed = True
                notes.append("no paired baseline items")
            else:
                delta, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=n_resamples,
                    rng=rng,
                    confidence=confidence,
                )

                notes.append(
                    f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                )

                if not all(math.isfinite(x) for x in (delta, lo, hi)):
                    failed = True
                    notes.append("invalid confidence interval")
                elif hi < 0:
                    failed = True
                    notes.append("significant regression")

        verdict = "BLOCK" if failed else "ok"

        if failed and blocking:
            blocked.append(slice_id)

        lines.append(
            f"  {slice_id:<35} "
            f"value={value:.3f} "
            f"{' | '.join(notes)} "
            f"[{verdict}]"
        )

    return blocked, lines


def check(
    pr: dict,
    base: dict,
    spec: dict,
    base_spec: dict | None = None,
) -> tuple[list[str], list[str]]:

    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return (
            ["eval_set_sha"],
            [
                "  EVAL SET differs from the baseline's: "
                "re-run the baseline on the same eval set"
            ],
        )

    problems = integrity_check(pr, base, spec, base_spec)

    if problems:
        return (
            ["integrity"],
            [f"  INTEGRITY {p}" for p in problems],
        )

    blocked: list[str] = []
    lines: list[str] = []

    bootstrap_cfg = spec.get("bootstrap", {})

    for metric in spec.get("metrics", []):
        mid = metric["id"]
        threshold = metric.get("threshold", {})
        value = pr["metrics"].get(mid)
        base_value = base["metrics"].get(mid)

        verdict = "ok"
        note = ""

        if value is None:
            verdict = "missing"

        elif "max" in threshold and value > threshold["max"]:
            verdict = "fail"

        elif "min" in threshold and value < threshold["min"]:
            verdict = "fail"

        elif (
            "max_increase" in threshold
            and base_value is not None
            and value > base_value * (1 + threshold["max_increase"])
        ):
            verdict = "fail"

        if threshold.get("no_significant_drop") and value is not None:
            pr_items = per_item(pr, mid)
            base_items = per_item(base, mid)

            keys = sorted(set(pr_items) & set(base_items))

            if not keys:
                verdict = "fail"
                note = "no paired items available"
            else:
                delta, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=bootstrap_cfg.get("n_resamples", 1000),
                    rng=bootstrap_cfg.get("rng", 2027),
                    confidence=bootstrap_cfg.get("confidence", 0.95),
                )

                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"

                if hi < 0:
                    verdict = "fail"

        is_blocking = metric.get("blocking", False)

        if verdict != "ok" and is_blocking:
            blocked.append(mid)

        label = (
            "ok"
            if verdict == "ok"
            else "MISSING"
            if verdict == "missing"
            else "BLOCK"
            if is_blocking
            else "warn"
        )

        lines.append(
            f"  {mid:<22} {value!s:<8} "
            f"{json.dumps(threshold):<40} "
            f"{note:<28} {label}"
        )

    if spec.get("slices"):
        slice_blocked, slice_lines = slice_check(pr, base, spec)
        blocked.extend(slice_blocked)
        lines.extend(slice_lines)

    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()

    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument(
        "--base-spec",
        help="metric spec on main, for the ratchet check (M7)",
    )

    args = ap.parse_args(argv)

    pr = json.loads(
        Path(args.pr).read_text(encoding="utf-8")
    )

    base = json.loads(
        Path(args.baseline).read_text(encoding="utf-8")
    )

    base_spec = (
        load_spec(Path(args.base_spec))
        if args.base_spec
        else None
    )

    blocked, lines = check(
        pr,
        base,
        load_spec(Path(args.spec)),
        base_spec,
    )

    print(
        f"gate: PR {pr['run_id']} vs main {base['run_id']} "
        f"· eval set {pr['manifest']['eval_set_sha']}"
    )

    print("\n".join(lines))

    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1

    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

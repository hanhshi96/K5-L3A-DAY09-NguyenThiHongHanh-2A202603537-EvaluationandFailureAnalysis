"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import numpy as np
from scipy.stats import bootstrap

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")

    h = [str(x).strip().upper() for x in human]
    j = [str(x).strip().upper() for x in judge]

    return {
        "tp": sum(a == POS and b == POS for a, b in zip(h, j)),
        "fp": sum(a != POS and b == POS for a, b in zip(h, j)),
        "fn": sum(a == POS and b != POS for a, b in zip(h, j)),
        "tn": sum(a != POS and b != POS for a, b in zip(h, j)),
    }


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    precision = cm["tp"] / (cm["tp"] + cm["fp"]) if cm["tp"] + cm["fp"] else 0.0
    recall = cm["tp"] / (cm["tp"] + cm["fn"]) if cm["tp"] + cm["fn"] else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    cm = confusion(human, judge)
    n = len(human)
    if n == 0:
        raise ValueError("kappa is undefined for empty labels")

    observed = (cm["tp"] + cm["tn"]) / n
    expected = (
        (cm["tp"] + cm["fn"]) * (cm["tp"] + cm["fp"])
        + (cm["fp"] + cm["tn"]) * (cm["fn"] + cm["tn"])
    ) / (n * n)

    if expected == 1:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (observed - expected) / (1 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    denominator = sensitivity + specificity - 1
    if denominator == 0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity = 1")

    estimate = (observed_rate + specificity - 1) / denominator
    return max(0.0, min(1.0, estimate))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    # TODO M4
    if len(a) != len(b):
        raise ValueError("a and b must have the same length")

    if len(a) == 0:
        raise ValueError("a and b must not be empty")

    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)

    if a_arr.ndim != 1 or b_arr.ndim != 1:
        raise ValueError("a and b must be one-dimensional")

    if np.array_equal(a_arr, b_arr):
        return (0.0, 0.0, 0.0)

    def mean_difference(x, y):
        return float(np.mean(x - y))

    observed = mean_difference(a_arr, b_arr)

    result = bootstrap(
        (a_arr, b_arr),
        statistic=mean_difference,
        paired=True,
        vectorized=False,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )

    return (
        float(observed),
        float(result.confidence_interval.low),
        float(result.confidence_interval.high),
    )



def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    # TODO M6
    raise NotImplementedError


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    # TODO M6
    raise NotImplementedError

# Failure taxonomy v1

| ID | Tên | Định nghĩa (1 câu) | Layer | Bằng chứng (claim@seed / trace) | Grader | Metric |
|---|---|---|---|---|---|---|
| FM-02 | ignore_denied — bỏ qua thao tác bị từ chối | Agent báo đã xử lý thành công dù host từ chối hoàn tiền. | guardrail/approval | `seeded_regression`, C-007@11: ledger ghi 0đ nhưng trạng thái là `resolved`; `fixed` trả `denied`. | code (`TrialPass`) | `pass_rate` |
| FM-03 | ticket_trust — tin ticket hơn DB | Agent dùng thông tin trong ticket để ghi đè dữ kiện đơn hàng đã tra từ DB. | model/prompt | `seeded_regression`, C-002@11, event 3 `model_override` với `delay_days: 5`; `fixed` không ghi đè và từ chối hoàn tiền. | code (`DbFactKept`) | `db_fact_kept` |
| FM-04 | sum_parts — cộng các khoản bồi thường | Agent cộng các khoản trong quote thay vì dùng số tiền quote chính thức, làm số tiền đề xuất sai. | orchestration/state | `slice_regression`, C-014@11: quote 150.000đ nhưng proposal 180.000đ; ledger ghi 150.000đ thay vì 120.000đ. | code (`RefundAmountCorrect`) | `refund_amount_correct` |
| FM-05 | pre_deducted — tự trừ khoản đã hoàn | Agent tự trừ tiền đã hoàn trước đó dù host sẽ áp dụng mức trần theo đơn lần nữa. | orchestration/state | `seeded_regression`, C-014@11: proposal 120.000đ, trước đó đã hoàn 30.000đ; host ghi 90.000đ thay vì 120.000đ. | code (`RefundAmountCorrect`) | `refund_amount_correct` |
| FM-08 | misreport — reply báo sai số tiền | Reply nêu số tiền đề xuất thay vì số tiền host thực sự ghi vào ledger. | orchestration/state | `seeded_regression`, C-014@11: reply báo 120.000đ nhưng ledger ghi 90.000đ. | code (grader cần bổ sung) | `reply_amount_matches_ledger` |

Các khoản tiền và quyết định approval phải được chấm bằng code; không dùng judge để quyết định đúng sai về tiền.
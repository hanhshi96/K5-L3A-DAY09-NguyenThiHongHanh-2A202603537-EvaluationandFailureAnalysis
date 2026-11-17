
# Judge audit — LogiX-VN

## 1. Kết quả hiệu chuẩn

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS? | Quyết định |
|---|---:|---:|---:|---:|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại |

Ngưỡng đánh giá:
- Cohen's Kappa >= 0.60
- Precision >= 0.80
- Recall >= 0.70

## 2. Audit thủ công các trường hợp bất đồng

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Human | Cách xưng hô "em" và từ "nha" tạo cảm giác quá suồng sã với khách hàng. Judge nhầm sự thân thiện với tính chuyên nghiệp. |
| 2 | H-017 | PASS | FAIL | Human | Cách gọi "bạn ơi" không phù hợp với khách hàng lớn tuổi. Cần đánh giá cả ngữ cảnh và quan hệ giao tiếp. |
| 3 | H-029 | PASS | FAIL | Human | Cụm "không cần nhắn thêm" mang tính ra lệnh, thiếu sự tôn trọng khách hàng. Judge chỉ chú ý các từ lịch sự ở đầu câu. |
| 4 | H-042 | FAIL | PASS | Human | Câu trả lời ngắn nhưng đầy đủ thông tin. Không nên bắt buộc mọi phản hồi đều phải có lời xin lỗi. |
| 5 | H-051 | FAIL | PASS | Human | Từ "refund" được CS LogiX cho phép sử dụng. Không nên đánh giá tiêu cực chỉ vì có từ tiếng Anh. |

## 3. Phân tích ma trận nhầm lẫn

### Tone judge

- TP = 24
- FP = 4
- FN = 6
- TN = 66

Tone judge đạt cả ba ngưỡng hiệu chuẩn. Tuy nhiên, vẫn còn 10 trường hợp bất đồng với nhãn người. Các lỗi chủ yếu liên quan đến cách xưng hô, sắc thái giao tiếp và việc đánh giá quá máy móc các tiêu chí như lời xin lỗi hoặc từ ngữ tiếng Anh.

### Helpful judge

- TP = 9
- FP = 0
- FN = 21
- TN = 70

Helpful judge có Precision = 1.000 nhưng Recall chỉ đạt 0.300. Điều này cho thấy judge hầu như không báo nhầm lỗi, nhưng bỏ sót 21/30 trường hợp thực sự có lỗi.

Đặc biệt, judge không phát hiện tốt các trường hợp sai số tiền hoàn trả dù phản hồi có cách diễn đạt lịch sự, dài và thể hiện sự đồng cảm. Vì vậy, không thể sử dụng helpful judge làm evaluation gate.

## 4. Hiệu chỉnh tỷ lệ lỗi

Sử dụng phương pháp Rogan-Gladen để điều chỉnh tỷ lệ lỗi quan sát được theo độ nhạy và độ đặc hiệu của judge.

- Tone: tỷ lệ lỗi quan sát 0.28, sau hiệu chỉnh là 0.30.
- Helpful: tỷ lệ lỗi quan sát 0.09, sau hiệu chỉnh là 0.30.

Kết quả cho thấy tỷ lệ lỗi quan sát của helpful judge thấp hơn thực tế do khả năng phát hiện lỗi kém.

## 5. Kết luận và quyết định sử dụng

- Chấp nhận tone judge làm tiêu chí đánh giá hỗ trợ trong evaluation gate vì đạt các ngưỡng Precision, Recall và Cohen's Kappa.
- Loại helpful judge khỏi evaluation gate vì Recall = 0.300 và Cohen's Kappa = 0.375, không đáp ứng yêu cầu độ tin cậy.
- Các lỗi liên quan đến số tiền hoàn trả, trạng thái giao dịch và quyền phê duyệt phải được kiểm tra bằng code-based graders thay vì phụ thuộc vào LLM judge.
- Cần tiếp tục audit thủ công và bổ sung nhãn người trên dữ liệu mới để kiểm tra khả năng tổng quát hóa.

### Rủi ro còn lại

Hai bộ dữ liệu hiệu chuẩn hiện tại chỉ là dữ liệu replay công khai. Kết quả đạt ngưỡng chưa chứng minh judge có thể hoạt động ổn định trên dữ liệu thực tế chưa từng được kiểm tra. Do đó, cần có tập dữ liệu held-out với nhãn do con người đánh giá độc lập.
# Judge audit

Hai bộ replay công khai có 100 reply mỗi bộ. Nhãn người chấm là mốc đối chiếu, FAIL là lớp dương. Judge đạt khi cả ba chỉ số đạt sàn κ ≥ 0,6, precision ≥ 0,8 và recall ≥ 0,7.

| Tiêu chí | κ | Precision | Recall | TP / FP / FN / TN | Tỷ lệ lỗi quan sát → hiệu chỉnh | Quyết định |
|---|---:|---:|---:|---|---|---|
| tone_ok | 0,757 | 0,857 | 0,800 | 24 / 4 / 6 / 66 | 28% → 30% | Đạt, dùng để đánh giá giọng điệu trong phạm vi bộ replay. |
| helpful | 0,375 | 1,000 | 0,300 | 9 / 0 / 21 / 70 | 9% → 30% | Loại khỏi gate. Recall và κ đều dưới sàn. |

## Các trường hợp bất đồng

| Case | Judge / Người | Kết luận audit và bằng chứng | Đề xuất sửa tiêu chí chấm |
|---|---|---|---|
| H-008 | PASS / FAIL | Đồng ý FAIL. Cách nói “rồi nha, anh check giúp em” quá thân mật theo chuẩn CS của bộ nhãn. | Thêm ví dụ phân biệt thân thiện với suồng sã dựa trên cả câu và cách xưng hô. |
| H-029 | PASS / FAIL | Đồng ý FAIL. Cụm “không cần nhắn thêm” yêu cầu khách ngừng liên hệ dù câu mở đầu lễ phép. | Đọc đến cuối reply và đánh dấu các câu ngăn khách tiếp tục trao đổi. |
| H-042 | FAIL / PASS | Đồng ý PASS. Reply xác nhận hoàn tiền, nêu thời gian chờ và kết thúc bằng “ạ”. Theo ghi chú, judge trừ điểm vì thiếu lời xin lỗi. | Cho phép xác nhận giao dịch ngắn, lịch sự; chỉ yêu cầu xin lỗi ở tình huống có lý do cụ thể. |
| H-051 | FAIL / PASS | Đồng ý PASS. Câu dùng từ “refund”, thuộc nhóm từ CS LogiX cho phép theo ghi chú. | Bổ sung từ nghiệp vụ được chấp nhận và ví dụ sử dụng lịch sự. |
| HL-015 | PASS / FAIL | Đồng ý FAIL. Reply báo hoàn 55.000đ cho O-112, ghi chú ledger là 40.000đ. | Kiểm số tiền được xác nhận bằng code trên ledger trước khi cho PASS. |
| HL-016 | PASS / FAIL | Đồng ý FAIL. Hai lời xin lỗi đi cùng xác nhận hoàn 55.000đ cho O-404, trong khi ghi chú ledger là 35.000đ. | Chấm độ chính xác của giao dịch độc lập với độ lịch sự và độ dài reply. |
| HL-020 | PASS / FAIL | Đồng ý FAIL. Reply báo 90.000đ cho O-303, thấp hơn mức 120.000đ trong ghi chú ledger. | Kiểm tra bằng nhau theo đơn vị đồng để bắt cả trường hợp báo thừa lẫn báo thiếu. |

## Quyết định sử dụng

Judge helpful chỉ bắt được 9 trong 30 lỗi người chấm xác nhận. Precision bằng 1 vì cả 9 lần báo lỗi đều đúng, nhưng 21 lỗi còn lại lọt qua. Hiệu chỉnh Rogan–Gladen đưa ước lượng tỷ lệ lỗi lên 30% ở cấp tập dữ liệu; quyết định trên từng reply vẫn cần được kiểm tra. Với các câu xác nhận hoàn tiền, có thể đối chiếu trực tiếp số tiền trong reply với ledger như ở M3.

Judge tone_ok đạt cả ba sàn nhưng vẫn bỏ sót 6 lỗi và báo nhầm 4 lần. Cần một bộ reply mới có nhãn người độc lập để kiểm tra hiệu quả sau khi sửa rubric. Các số liệu ở đây chỉ mô tả hai CSV công khai.

## Tái hiện từ thư mục src

~~~powershell
.\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
.\.venv\Scripts\python.exe -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
~~~

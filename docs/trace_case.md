# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## C-002, seed 11

| Trường | Nội dung |
|---|---|
| Trial | `R-seeded_regression-C-002-s11` (run ID của trace). |
| Triệu chứng | Kết quả là `resolved`, trong khi nhãn là `denied`. Reply và ledger đều ghi 20.000đ. Nhãn yêu cầu 0 giao dịch và 0đ. |
| Bước sai đầu tiên | Event 3, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Event 1 bàn giao yêu cầu kiểm chính sách. Event 2 đọc đơn O-202 với 2 ngày trễ. Đến event 3, agent mới thay bằng 5 ngày trong ticket. |
| Failure mode | FM-03, tin ticket hơn dữ kiện trong DB. |
| Đối chứng | Với `fixed`, event 3 là `quote` 0đ, lý do `no_entitlement`. Kết quả là `denied`, ledger có 0 giao dịch. |
| Regression test | `test_c002_uses_order_delay` đối chiếu bộ ba trạng thái, số giao dịch và tiền thực ghi với nhãn cho cả hai variant. |
| Giới hạn | Ledger là dữ liệu mô phỏng. Một trial chứng minh được quyết định sai ở seed 11. Tần suất lỗi cần đo trên nhiều seed. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.

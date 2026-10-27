# Linko Backend V6 – CRUD an toàn trên Oracle 23ai

Bản nâng cấp này sử dụng các **7 bảng Oracle hiện có**, không thêm bảng, không cần `DROP TABLE` hoặc migration DDL từ V5.

## Thêm mới

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | `/api/data/employees/{id}/delete-impact` | Xem quan hệ phụ thuộc trước khi xóa nhân viên |
| GET | `/api/data/projects/{id}/delete-impact` | Xem số thành viên liên quan trước khi xóa dự án |
| GET | `/api/data/departments/{id}/delete-impact` | Xem số nhân viên và dự án trực thuộc |
| PATCH | `/api/data/employees/{id}/status` | ACTIVE / INACTIVE / ON_LEAVE |
| POST | `/api/data/employees/bulk-status` | Cập nhật hàng loạt tối đa 100 nhân viên, atomic |
| POST | `/api/data/departments/{id}/transfer` | Chuyển nhân viên / dự án sang phòng ban khác trong 1 transaction |
| PUT | `/api/data/projects/{pid}/members/{eid}` | Thêm thành viên mới hoặc sửa vai trò/ngày tham gia |
| GET | `/api/data/connections/{from}/{to}` | Chi tiết quan hệ social |
| PATCH | `/api/data/connections/{from}/{to}` | Sửa quan hệ + audit trigger |
| DELETE | `/api/data/connections/{from}/{to}` | Xóa quan hệ + audit trigger |

## Endpoint cũ được nâng cấp

- `DELETE /api/employees/{id}`: mặc định chặn khi có manager/subordinates/memberships/social links; `?cascade=true&confirm=true` cho phép xóa có chủ đích, gỡ liên kết trong 1 transaction.
- `DELETE /api/projects/{id}`: mặc định chặn khi còn members; `?cascade=true&confirm=true` gỡ membership trước để trigger cập nhật TEAMMATE.
- `DELETE /api/departments/{id}`: luôn chặn nếu còn nhân viên hoặc dự án. Dùng endpoint `transfer` trước.
- `PUT /api/connections` / `DELETE /api/connections`: chặn sửa/xóa quan hệ TEAMMATE tự sinh (`notes` có tiền tố dành riêng cho trigger). Không cho người dùng tạo giả tiền tố này.

**Lưu ý:** Xóa liên đới nhân viên sẽ làm các cấp dưới trực tiếp mất quản lý. Không tự động xóa các nhân viên cấp dưới. Các log KN OWS vẫn giữ trong `audit_log`.

## Kiểm thử

- `python -m unittest discover -s tests -v` – kiểm thử hợp đồng HTTP và giao dịch offline.
- `python tools/doctor.py` – kiểm tra cấu hình, môi trường và Oracle (nếu có).
- `python tools/smoke_crud_v6.py --write` – thử **INSERT/PATCH/DELETE thật** qua HTTP đến Oracle. Chỉ chạy trên PDB test/demo, công cụ tự tạo record có prefix `V6_TEST` và cố gắng dọn các record đó. Cần server đang chạy.

Các test offline **không chứng minh cú pháp GRAPH_TABLE/trigger chạy được trên Oracle 23ai thật**; phải chạy smoke test trên database người dùng để xác nhận.

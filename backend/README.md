# V7 RELEASE

**Xem [README_V7_DEPLOY.md](README_V7_DEPLOY.md) trước khi chạy**. Phần dưới mô tả phiên bản cũ V5/V6; cơ chế `API_WRITE_KEY` đã bị thay bằng JWT và `DELETE /api/employees/{id}` mặc định soft-delete ở V7.

---

# Linko Backend V5 — Oracle 23ai Real API

**Nhóm 13 · Đề tài 17 · FastAPI + Oracle Database 23ai (SQL Property Graph)**

Backend V5 chạy truy vấn Oracle thật, **không có SQLite, mock fallback hay JSON dữ liệu giả**. Chỉ phần unit test offline dùng test doubles để kiểm tra contract. Backend này *chưa được kiểm chứng trên một Oracle server trong môi trường đóng gói*; dùng `tools/doctor.py` và `tools/smoke_http.py` để chứng minh hoạt động trên PDB của bạn.

## 1. V4 → V5 đã sửa gì?

- Một transaction per HTTP request: `db_action(write=True)` tự **COMMIT sau cùng** khi mọi bước thành công; lỗi tự **ROLLBACK**. Đã bỏ COMMIT/ROLLBACK lẫn trong service và `pkg_social_network.create_connection` (mã package V5).
- Trigger `trg_auto_teammate` **compound trigger** xử lý INSERT, UPDATE và DELETE trên `project_members`. Khi hết dự án chung, chỉ xóa `Knows` TEAMMATE **do trigger sinh**; quan hệ FRIEND, MENTOR hoặc quan hệ tạo tay không bị xóa. Nếu vẫn cùng dự án khác, giữ kết nối.
- Cài lại trigger và chạy `08_reconcile_teammates.sql` để backfill TEAMMATE cho dữ liệu mẫu (V4 nạp sample trước khi tạo trigger) và dọn cạnh tự sinh lỗi thời.
- Gán quản lý (`PUT /api/employees/{id}/manager`) sử dụng khóa bảng `reports_to` khi kiểm tra chu trình, giảm race condition giữa **các request API**. Những SQL DML trực tiếp ở ngoài backend vẫn cần được bảo vệ riêng.
- `/api/ready` thử kiểm tra kết nối, object và `GRAPH_TABLE` thật. `/api/network/integrity` phát hiện TEAMMATE bị lỗi; thống kê hợp tác dự án & xuyên phòng ban.
- `/api/graph/overview` chỉ query cạnh có 2 đầu nằm trong tập node đã chọn, giới hạn 5.000 cạnh và trả `truncated_edges`.
- Tùy chọn `API_WRITE_KEY`, CORS giới hạn origin, và `X-Request-ID` để tra log. Đây **không phải** giải pháp đăng nhập/phân quyền đầy đủ.
- Giữ endpoints V4 để frontend không bắt buộc sửa lại. **62 HTTP operations** được Swagger mô tả (gồm PUT/PATCH của cùng đường dẫn).

## 2. Yêu cầu trước khi chạy

- Oracle Database **23ai Release Update 23.8+** để hỗ trợ `MATCHNUM` / `ELEMENT_NUMBER` với `ONE ROW PER STEP` (xem [Oracle Graph 23ai release updates](https://docs.oracle.com/en/database/oracle/property-graph/24.4/spgdg/key-property-graph-features-oracle-database-release-23ai.html)).
- PDB, listener TCP đang chạy, schema riêng `SOCIAL_NETWORK` được cấp quyền tạo table, trigger, package, property graph. Không dùng SYS/SYSTEM để chạy ứng dụng.
- Python 3.10+, SQL Developer/SQLcl/SQL*Plus để chạy script `@...`.

### Dữ liệu mới hoàn toàn (có xóa dữ liệu 7 bảng)

> **CẢNH BÁO:** `INSTALL.sql` DROP 7 bảng cũ và tạo lại bảng. Chỉ chạy trên schema demo mới/đã backup.

Đăng nhập bằng **schema ứng dụng** trong SQLcl hoặc SQL Developer (F5), chạy:

```sql
@/duong-dan/backend/sql/setup/INSTALL.sql
```

Thứ tự: schema → sample data → property graph → package/triggers → V5 compound trigger → reconcile TEAMMATE → validation.

### Nâng V4 lên V5 mà **không xóa 7 bảng**

> **Sao lưu PDB trước khi chạy.** Oracle DDL tự COMMIT; migration thay thế package và trigger, rồi có thể thay đổi/xóa *các Knows TEAMMATE tự sinh đã lỗi thời* qua reconciliation. Không chạy cùng lúc với traffic ghi API.

SQLcl/SQL Developer (F5) bằng schema sở hữu đồ thị:

```sql
@/duong-dan/backend/sql/setup/MIGRATE_V4_TO_V5.sql
```

`MIGRATE_V4_TO_V5.sql` chỉ tái biên dịch `04_plsql.sql`, thay `trg_auto_teammate`, reconcile dữ liệu, kiểm tra object. Script không DROP bảng. Cần chạy migration **trước** khi bật backend V5 vì service phụ thuộc package không tự COMMIT và trigger mới.

## 3. Chạy backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` → `.env` rồi cập nhật:

```dotenv
DB_USER=SOCIAL_NETWORK
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=1521
DB_SERVICE=FREEPDB1
# Bỏ trống khi chỉ demo local; điền key khi cần hạn chế quyền ghi
API_WRITE_KEY=
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

```bash
python tools/doctor.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger API: <http://127.0.0.1:8000/docs>. `GET /api/live` chỉ kiểm tra process; `GET /api/health` kiểm tra Oracle; **`GET /api/ready` còn kiểm tra schema và câu GRAPH_TABLE**. Nếu database chưa sẵn sàng, backend không xuất mock success.

## 4. Test

Offline (không cần Oracle):

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

HTTP lên Oracle thật (chạy terminal khác khi server đã mở):

```bash
python tools/smoke_http.py
```

Kiểm thử ghi/xóa thật chỉ trên **PDB demo có thể xóa dữ liệu**:

```bash
python tools/smoke_http.py --write
# Nếu đã bật API_WRITE_KEY:
python tools/smoke_http.py --write --api-key "your_key"
```

Test này tạo **2 nhân viên, 2 dự án, 1 phòng ban tạm**, gán thành viên, xác nhận TEAMMATE 2 chiều, gỡ khỏi 1 dự án (vẫn giữ quan hệ), rồi gỡ dự án cuối (xóa cạnh tự sinh), sau đó cố gắng cleanup dữ liệu. Mỗi request ghi có COMMIT thật và cleanup không thể đảm bảo khi mất mạng/quyền DB; tuyệt đối không dùng trên production. Kết quả kiểm thử *chỉ được coi thành công khi lệnh exit 0 trên máy có Oracle*.

## 5. API quan trọng

| Method | Path | Mục đích |
|---|---|---|
| GET | `/api/ready` | Health Oracle/schema/graph |
| GET | `/api/employees`, `/api/departments`, `/api/projects` | Danh mục |
| POST/PATCH/DELETE | `/api/employees/{id}` và `POST /api/employees` | CRUD nhân viên |
| POST/PATCH/DELETE | `/api/projects/{id}` và `POST /api/projects` | CRUD dự án |
| POST/GET/PATCH/DELETE | `/api/projects/{id}/members[/{emp}]` | Thành viên, đồng bộ TEAMMATE |
| GET/PUT/DELETE | `/api/employees/{id}/manager` | Quản lý trực tiếp, chặn chu trình trong API |
| GET/POST/PUT/DELETE | `/api/connections` | Quan hệ xã hội, audit trigger |
| POST | `/api/graph/shortest-path` | Shortest path + Cytoscape elements từ GRAPH_TABLE |
| GET | `/api/graph/teammates/{id}` | Đồng đội cùng dự án |
| GET | `/api/graph/subordinates/{id}` | Cấp dưới nhiều tầng |
| GET | `/api/graph/khops/{id}?k=2` | k-hops |
| GET | `/api/graph/overview` | Graph tổng quan; cờ truncated_edges |
| GET | `/api/network/integrity` | Phát hiện TEAMMATE thiếu/stale |
| GET | `/api/stats/cross-department` | Liên kết khác phòng ban |
| GET | `/api/stats/project-collaboration` | Số thành viên/phòng ban mỗi dự án |
| GET | `/api/audit-logs` | Nhật ký quan hệ |

Swagger tại `/docs` là danh sách method/route chính xác nhất. Các đường dẫn V7-compat hỗ trợ **Directory/Graph** nhưng chưa hỗ trợ đăng nhập, newsfeed, chat, backup/restore/reset (ngoài đề tài 17 và 7 bảng Oracle).

## 6. Hạn chế chưa được giải quyết

1. **Chưa có Oracle server kiểm thử trong môi trường tạo ZIP**; PL/SQL, trigger và GRAPH_TABLE cần chạy thử trên đúng RU 23ai của nhóm.
2. `pkg_social_network.find_shortest_path_length` vẫn quét `{1,6}` cố định (API kiểm tra max_hops ở lớp trả kết quả); chưa tối ưu theo độ sâu k. Graph dày có thể tốn tài nguyên lớn.
3. Compound trigger đánh dấu sở hữu bằng `knows.notes = 'Auto-created from project ...'`; đây là cách sửa giữ nguyên 7 bảng, **không phải provenance có khóa ngoại**. Nếu người dùng sửa ghi chú/kết nối tự sinh, hệ thống có thể không nhận ra để đồng bộ. Hệ thống production nên tách một bảng nguồn gốc quan hệ.
4. Nếu có nhiều phiên trực tiếp INSERT vào `project_members` **cùng lúc** ngoài API, cần thêm cơ chế đồng bộ ghi/khóa để đảm bảo không bỏ sót quan hệ sinh tự động. Chưa có test concurrency thực tế trên Oracle.
5. `API_WRITE_KEY` chỉ bảo vệ method ghi ở `/api/` khi được cấu hình; không có đăng nhập, vai trò HR/admin, audit user cá nhân, TLS hay rate limiting. Chỉ chạy local hoặc sau reverse proxy tin cậy khi demo.

## 7. Troubleshooting

- `ModuleNotFoundError: oracledb`: cài requirements trong môi trường Python hiện tại.
- `/api/live = 200` nhưng `/api/ready` lỗi: kiểm tra `.env`, schema, trigger/PLSQL graph, chạy `tools/doctor.py`.
- `ORA-04091`: trigger cũ; chạy `MIGRATE_V4_TO_V5.sql`, xem `USER_ERRORS`.
- `ORA-01017`: sai user/password hoặc PDB.
- `ORA-12541` / `DPY-6005`: listener/port/service chưa đúng.
- `ORA-06508` / `ORA-04063`: package/trigger invalid, kiểm tra `USER_ERRORS`.
- Graph function `MATCHNUM` / `ELEMENT_NUMBER` lỗi: kiểm tra Release Update 23.8+.
- API ghi HTTP 401: cấu hình `X-API-Key` theo `API_WRITE_KEY` (cũng bảo vệ POST `/api/graph/shortest-path`).

---

## V6 – Sửa, xóa, cập nhật dữ liệu Oracle (không mock)

Xem chi tiết trong `CHANGELOG_V6.md`. Các API hiện có từ V5 vẫn giữ URL.

### Ví dụ thao tác từ Swagger `/docs`

1. `POST /api/employees`: `{ "full_name":"Nguyễn Văn Mẫu", "email":"mau.v6@example.test", "department_id":2 }` để tạo nhân viên.
2. `PATCH /api/employees/120`: `{ "title":"Tech Lead", "phone":"0900000000" }` để sửa các trường có mặt; trường bỏ qua sẽ giữ nguyên.
3. `POST /api/data/employees/bulk-status`: `{ "employee_ids":[20,21], "status":"ON_LEAVE" }` để cập nhật nhiều người một lần.
4. `GET /api/data/employees/120/delete-impact` để xem liên kết, rồi `DELETE /api/employees/120`. Nếu đang có liên kết và thật sự cần xóa liên đới thì sử dụng `?cascade=true&confirm=true` sau khi xem tác động.
5. `PUT /api/data/projects/1/members/20`: `{ "role":"TECH_LEAD", "join_date":"2026-10-01" }` để gán/thay vai trò dự án; trigger duy trì TEAMMATE.
6. `PATCH /api/data/connections/20/11`: `{ "strength":4.5, "notes":"Đã phối hợp thực tế" }`; audit_log tự ghi thay đổi.
7. `POST /api/data/departments/9/transfer`: `{ "target_department_id":2, "move_employees":true, "move_projects":true }` để chuyển dữ liệu trước khi xóa phòng ban.

**Lưu ý:** `?cascade=true&confirm=true` xóa cứng các quan hệ phụ thuộc, không thể khôi phục nếu không có bản sao lưu. API_WRITE_KEY chỉ là bảo vệ API demo, không tương đương hệ thống phân quyền người dùng.

### Test CRUD bằng HTTP + Oracle thật

Sau khi hoàn thành SQL setup V5, chạy server ở `http://127.0.0.1:8000` và bảo đảm `GET /api/ready` trả `ready`:

```bash
python tools/smoke_crud_v6.py --write
```

Không chạy test ghi/xóa trên database quan trọng. Smoke script tạo dữ liệu độc lập, dọn dữ liệu khi thành công và thử cleanup khi thất bại (không thể bảo đảm cleanup trong mọi loại sự cố).

# Linko V7 – Backend Oracle 23ai, role-based JWT, safe CRUD & DB audit

**Đề tài 17 / Nhóm 13 HUFLIT.** Code chạy Oracle-only, không có fallback SQLite/mock ở HTTP runtime. `GET /api/live` không kiểm tra Oracle, `GET /api/ready` có kiểm tra schema + GRAPH_TABLE thật. **CHƯA được xác nhận hoạt động trên Oracle 23ai ở môi trường tạo ZIP**: unit/offline tests ≠ integration tests.

## Những điểm khác V6

- Xóa `API_WRITE_KEY` chia sẻ cho frontend. V7 yêu cầu JWT cho **tất cả API ngoại trừ `/api/live`**, kể cả `POST /api/graph/shortest-path` chỉ cần vai trò Employee.
- Vai trò: `employee` xem danh bạ/graph; `hr` thêm/sửa + xem audit/delete-impact; `admin` được phép xóa (kể cả hard delete và xóa membership). Quy tắc tối thiểu, cần xem lại theo chính sách doanh nghiệp.
- Local JWT chỉ dùng để demo offline/nhóm nội bộ. Production sử dụng `AUTH_MODE=oidc`, JWT ký RS256, validate issuer/audience/JWKS HTTPS từ SSO/IdP. Không có endpoint cấp JWT công khai.
- `DELETE /api/employees/{id}` giờ **soft delete** (status=INACTIVE, giữ FK). Muốn **hard delete** phải `?hard=true&confirm=true`, và thêm `cascade=true` nếu còn phụ thuộc. **Không cho xóa cứng quản lý còn direct reports** (phải chuyển quản lý cho cấp dưới trước). Vai trò Admin bắt buộc.
- Khi tìm đường bằng GRAPH_TABLE, chặng đi qua Employee không ACTIVE bị loại. Chọn đường ngắn nhất hợp lệ theo hop từ các kết quả có kiểm tra trạng thái; vẫn có giới hạn 30.000 dòng và `max_hops<=6` để chặn explosion.
- `09_v7_full_audit.sql` thêm 5 trigger và thay `trg_audit_knows`: lưu người thao tác từ `client_identifier` trên pooled connection, audit 6 bảng EMPLOYEES, DEPARTMENTS, PROJECTS, PROJECT_MEMBERS, REPORTS_TO, KNOWS. Audit trong cùng giao dịch để rollback đồng bộ. Không log email/số điện thoại; người sở hữu CSDL vẫn có thể sửa log, không phải audit bất biến.
- Có Dockerfile chạy non-root, compose localhost-only, `.dockerignore`, GitHub Actions test offline, Swagger Authorize Bearer, scripts smoke dùng `LINKO_TOKEN`.

## Yêu cầu kỹ thuật

- Oracle Database 23ai **RU 23.8+** cần cho các truy vấn step path `MATCHNUM()`/`ELEMENT_NUMBER()`. Cần thử thực sự với RU đang sử dụng.
- Python 3.12 đề xuất, `python-oracledb` Thin Mode, schema có 7 bảng và SQL Property Graph `enterprise_social_graph` cùng package/compound trigger V5.
- Cấu hình TLS qua HTTPS reverse proxy; **KHÔNG** public port uvicorn không mã hóa ra Internet.

## 1. Nâng V6 lên V7, giữ dữ liệu cũ

Backup Oracle schema/PDB, tạm dừng request ghi, chạy SQLcl/SQL*Plus hoặc SQL Developer (F5) dưới tài khoản chủ sở hữu schema:

```sql
@/absolute/path/backend/sql/setup/MIGRATE_V6_TO_V7.sql
```

Migration không `DROP TABLE`; có DDL nên Oracle tự commit, cần backup và khung bảo trì. `INSTALL.sql` là **CÀI MỚI CÓ XÓA 7 BẢNG**, đừng chạy nếu cần giữ dữ liệu. Dưới schema thiếu quyền đọc `V$VERSION`, câu validation trong `06_validation.sql` có thể cần quyền bổ sung; xem lỗi và xác nhận các object `VALID` trong `USER_OBJECTS`.

## 2. Cài backend và cấu hình JWT local demo

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Điền `.env`: DB_* + `AUTH_MODE=local`, đặt `JWT_SECRET` bằng chuỗi ngẫu nhiên vừa tạo (không commit `.env`); `CORS_ORIGINS` theo frontend. Dùng token được tạo bởi admin trên máy backend, **không gửi JWT_SECRET đến trình duyệt**:

```bash
python tools/issue_demo_token.py --sub demo-hr --role hr
python tools/issue_demo_token.py --sub demo-admin --role admin
```

```bash
python tools/doctor.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000/docs`, bấm **Authorize**, dán JWT (không nhập chữ Bearer nếu Swagger tự chèn). `/api/live` công khai; `/api/ready` và `/api/health` yêu cầu token HR.

## 3. Production SSO/OIDC

Đặt `AUTH_MODE=oidc`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` (HTTPS) từ nhà cung cấp đăng nhập công ty. IdP phải phát access token có `sub`, `exp`, `iat`, `iss`, `aud`, `roles` (array gồm employee/hr/admin). Ánh xạ vai trò tại IdP, không cho người dùng tự gán role. Không chấp nhận thuật toán `none` hay token tự ký HS256 trong OIDC mode.

Token gửi trong `Authorization: Bearer <jwt>`. API không cung cấp endpoint login/password; frontend phải đăng nhập qua giải pháp OIDC Authorization Code + PKCE do công ty chọn. Cấp phát, thu hồi quyền người dùng, MFA, quản trị thiết bị, refresh/revocation là trách nhiệm của IdP/gateway – V7 **chưa triển khai** những hệ thống đó.

## 4. Docker (API + Oracle bên ngoài)

```bash
docker compose up --build -d
```

Compose chỉ bind `127.0.0.1:8000`, không publish Internet, và **không triển khai Oracle container**. Nếu Oracle chạy trên máy host, đặt `DB_HOST=host.docker.internal` trong `.env` và thêm host gateway vào Docker trên Linux; nếu Oracle remote, dùng IP/DNS mà container truy cập được. DB password và JWT_SECRET chỉ trong `.env` bí mật, không commit. Dùng reverse proxy HTTPS và giới hạn request size/rate limit ở reverse proxy/gateway. `GET /api/live` làm liveness; readiness có JWT. Sizing pool theo số replicas.

## 5. Kiểm thử

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Test offline sử dụng `AUTH_MODE=test` qua test module, nhưng `AUTH_MODE=test` **bị từ chối trong môi trường production**. Đừng đưa test bypass vào `.env` thật.

**Kiểm tra trên Oracle thật:** gán biến `LINKO_TOKEN` = JWT của admin (không commit/ghi ra log), backend phải đang chạy.

```bash
python tools/doctor.py
python tools/smoke_http.py
# CHỈ trên schema disposable / demo
python tools/smoke_crud_v6.py --write
```

Những script trên kiểm tra đường đi HTTP → FastAPI → Oracle. `--write` tạo/xóa bản ghi, sẽ cố gắng cleanup, không đảm bảo nếu mất kết nối giữa chừng. Không chạy --write trên dữ liệu sản xuất.

## 6. Chưa thể xác nhận production-ready

Bắt buộc trước go-live: E2E Oracle 23ai RU thực tế, phép thử graph 1..6 hops trên dữ liệu lớn, stress/concurrency load test, backup/restore có diễn tập, migration rollback plan, rate limiting ở gateway, bảo mật IdP và MFA, monitoring, log retention/GDPR-nội bộ, CI với DB tích hợp. `09_v7_full_audit.sql` không thay thế audit theo chính sách bất biến/WORM. V7 tập trung chỉnh trực tiếp phần mềm, **chưa chứng minh** SLA/performance/an ninh của hạ tầng thực.

# Linko API v3.0

FastAPI · Oracle 23ai SQL Property Graph · Đề tài 17 · Nhóm 13

## Chạy

```bash
pip install -r requirements.txt
USE_MOCK=true uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger: http://localhost:8000/docs  
- Health: `/api/health`  
- Metrics: `/api/metrics`  
- Route map: `/api/openapi/summary`  

## Versioning

- `/api/*` chính  
- `/api/v1/*` alias (rewrite)  
- Headers: `X-API-Version: 3.0.0`, `X-Request-ID`, `X-Process-Time`  
- GZip tự động cho response ≥ 500 bytes  

## Graph (v3)

| Endpoint | Mô tả |
|----------|--------|
| `POST /api/paths/shortest` | Đường ngắn nhất |
| `POST /api/paths/shortest/filtered` | Lọc theo loại cạnh |
| `GET /api/paths/k-shortest` | K đường ngắn |
| `GET /api/paths/exists` | Có đường? |
| `GET /api/graph/neighborhood/{id}` | Ego-network |
| `GET /api/graph/centrality` | Degree ranking |
| `GET /api/graph/components` | Thành phần liên thông |
| `GET /api/graph/diameter` | Ước lượng đường kính |
| `GET /api/graph/edges` | Liệt kê cạnh |
| `GET /api/graph/degree/{id}` | Bậc đỉnh |
| `GET /api/connections` | Cạnh + phân trang |
| `DELETE /api/connections` | Xóa cạnh MOCK |

## Data / Employees

| Endpoint | Mô tả |
|----------|--------|
| CRUD `/api/employees` | Tạo/sửa/xóa |
| `POST /api/employees/batch` | Tạo hàng loạt |
| `DELETE /api/employees/batch` | Xóa hàng loạt |
| `GET /api/search/employees` | Tìm + phân trang |
| `POST /api/employees/compare` | So sánh 2 NV |
| `GET /api/export/employees.csv` | Xuất CSV |
| `GET /api/export/edges.csv` | Xuất cạnh CSV |
| Backup/restore/reset | `/api/data/*` |

## Oracle

```bash
USE_MOCK=false ORACLE_USER=system ORACLE_PASSWORD=... \
ORACLE_CONNECT_STRING=localhost:1521/lab04 \
uvicorn main:app --port 8000
```

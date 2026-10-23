# Linko Web

Ứng dụng mạng quan hệ nội bộ — Đề tài 17, Nhóm 13 (HUFLIT).

## Chạy

```bash
# API
cd ../linko-fastapi
pip install fastapi uvicorn oracledb python-dotenv
USE_MOCK=true uvicorn main:app --port 8000 --reload

# Web
cd ../linko-web
npm install
npm run dev
```

- Web: http://localhost:5173  
- API docs: http://localhost:8000/docs  
- Phím tắt: `Ctrl+K` tìm NV · Dark mode trên topbar

## Tính năng

- Tìm đường ngắn nhất + sơ đồ + lịch sử + copy
- Bạn chung, cây tổ chức, đồ thị mạng
- CRUD nhân viên, phòng ban, dự án
- Nhật ký quan hệ, dashboard thống kê live
- Dark mode, toast, global search

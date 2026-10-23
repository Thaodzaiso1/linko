import { memo, useRef, useState } from 'react';
import { api } from '../api/client';
import { toast } from '../components/Toast';
import { useAuth } from '../auth/AuthContext';

function DataPageInner() {
  const { user, can } = useAuth();
  const role = user!.role;
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const backup = async () => {
    setBusy(true);
    setInfo('');
    try {
      const data = await api.dataBackup();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      a.href = url;
      a.download = `linko-backup-${ts}.json`;
      a.click();
      URL.revokeObjectURL(url);
      const emp = Array.isArray(data.employees) ? data.employees.length : '?';
      const edges = Array.isArray(data.edges) ? data.edges.length : '?';
      setInfo(`Đã tải backup: ${emp} NV, ${edges} cạnh`);
      toast('ok', 'Đã sao lưu dữ liệu (JSON)');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Sao lưu thất bại';
      setInfo(msg);
      toast('err', msg);
    } finally {
      setBusy(false);
    }
  };

  const onFile = async (file: File) => {
    setBusy(true);
    setInfo('');
    try {
      const text = await file.text();
      const json = JSON.parse(text) as Record<string, unknown>;
      if (!json.employees && !json.edges) {
        throw new Error('File không hợp lệ (thiếu employees/edges)');
      }
      if (!confirm('Khôi phục sẽ ghi đè dữ liệu MOCK hiện tại. Tiếp tục?')) {
        setBusy(false);
        return;
      }
      const r = await api.dataRestore(json);
      setInfo(r.message || `OK — ${r.employees} NV, ${r.edges} cạnh`);
      toast('ok', r.message || 'Đã khôi phục');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Khôi phục thất bại';
      setInfo(msg);
      toast('err', msg);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const reset = async () => {
    if (!confirm('Reset về snapshot lúc khởi động server?')) return;
    setBusy(true);
    setInfo('');
    try {
      const r = await api.dataReset();
      setInfo(r.message || 'Đã reset');
      toast('ok', r.message || 'Đã reset');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Reset thất bại';
      setInfo(msg);
      toast('err', msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {role === 'viewer' && (
        <div className="alert alert-err">Tài khoản viewer không được truy cập sao lưu.</div>
      )}
      {role === 'manager' && (
        <div className="alert alert-info">Manager: được sao lưu; restore/reset chỉ admin.</div>
      )}
      <div className="hero-banner">
        <h2>Sao lưu &amp; khôi phục</h2>
        <p>
          Xuất toàn bộ nhân viên, phòng ban, dự án và cạnh graph ra file JSON. Khôi phục lại khi demo
          hoặc sau khi thử CRUD.
        </p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">💾 Sao lưu</div>
          <p className="card-desc">
            Tải file <code>linko-backup-….json</code> chứa employees, departments, projects, edges.
          </p>
          <button type="button" className="btn btn-primary" disabled={busy || !can.canBackup(role)} onClick={backup}>
            {busy ? 'Đang xử lý…' : '⬇ Tải file sao lưu'}
          </button>
        </div>

        <div className="card">
          <div className="card-title">⬆ Khôi phục</div>
          <p className="card-desc">
            Chọn file JSON backup đã xuất trước đó. Chỉ áp dụng chế độ <strong>MOCK</strong>.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onFile(f);
            }}
          />
          <button
            type="button"
            className="btn btn-ghost"
            disabled={busy || !can.canRestore(role)}
            onClick={() => fileRef.current?.click()}
          >
            Chọn file khôi phục…
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">↺ Reset về mặc định</div>
        <p className="card-desc">
          Khôi phục snapshot lúc server khởi động (dữ liệu mẫu ban đầu), bỏ mọi thay đổi CRUD trong
          phiên MOCK.
        </p>
        <button type="button" className="btn btn-danger" disabled={busy || !can.canReset(role)} onClick={reset}>
          Reset dữ liệu mẫu
        </button>
        {info && (
          <div className={`alert ${info.includes('thất') || info.includes('Lỗi') || info.includes('501') ? 'alert-err' : 'alert-ok'}`} style={{ marginTop: 14 }}>
            {info}
          </div>
        )}
      </div>

      
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-title">Export CSV</div>
        <p className="card-desc">Download tabular dumps from API v3.</p>
        <div className="form-row">
          <a className="btn btn-ghost" href={api.exportEmployeesCsvUrl()} download>
            Employees CSV
          </a>
          <a className="btn btn-ghost" href={api.exportEdgesCsvUrl()} download>
            Edges CSV
          </a>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Lưu ý</div>
        <ul className="list">
          <li>
            <span>MOCK: backup/restore/reset hoạt động đầy đủ trên RAM server</span>
            <span className="tag tag-wo">OK</span>
          </li>
          <li>
            <span>Oracle: backup có thể đọc bảng; restore qua API demo chưa ghi Oracle</span>
            <span className="tag tag-kn">Limit</span>
          </li>
        </ul>
      </div>
    </>
  );
}

export const DataPage = memo(DataPageInner);

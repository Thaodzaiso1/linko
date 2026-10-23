import { memo, useEffect, useState } from 'react';
import { api } from '../api/client';

function AuditPageInner() {
  const [rows, setRows] = useState<
    {
      id: number;
      action: string;
      from_name?: string;
      to_name?: string;
      label?: string;
      at?: string;
    }[]
  >([]);
  const [err, setErr] = useState('');

  useEffect(() => {
    api
      .auditRecent(30)
      .then(setRows)
      .catch((e) => setErr(e instanceof Error ? e.message : 'Lỗi'));
  }, []);

  return (
    <div className="card">
      <div className="card-title">Nhật ký quan hệ (Audit)</div>
      <p className="card-desc">
        MOCK: tổng hợp từ cạnh graph. Oracle: bảng <code>audit_log</code> (trigger trg_audit_knows).
      </p>
      {err && <div className="alert alert-err">{err}</div>}
      <ul className="list">
        {rows.map((r) => (
          <li key={r.id}>
            <span>
              <span className={`tag ${r.action.includes('Knows') ? 'tag-kn' : r.action.includes('Reports') ? 'tag-rt' : 'tag-wo'}`}>
                {r.action.replace('EDGE_', '')}
              </span>{' '}
              <strong>{r.from_name}</strong>
              {' → '}
              <strong>{r.to_name}</strong>
              {r.label ? <span style={{ color: 'var(--muted)' }}> · {r.label}</span> : null}
            </span>
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>{r.at || ''}</span>
          </li>
        ))}
      </ul>
      {!rows.length && !err && <div className="empty">Chưa có bản ghi</div>}
    </div>
  );
}

export const AuditPage = memo(AuditPageInner);

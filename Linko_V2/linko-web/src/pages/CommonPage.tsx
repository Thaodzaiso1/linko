import { memo, useEffect, useState } from 'react';
import { api, type Employee } from '../api/client';

type Props = { onSelectEmp: (id: number) => void };

function CommonPageInner({ onSelectEmp }: Props) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [a, setA] = useState(8);
  const [b, setB] = useState(23);
  const [common, setCommon] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.employees().then((list) => {
      setEmployees(list);
      if (list.length >= 2) {
        setA(list[0].employee_id);
        setB(list[1].employee_id);
      }
    }).catch(() => setErr('Không tải NV'));
  }, []);

  const run = async () => {
    setLoading(true);
    setErr('');
    try {
      const rows = await api.commonConnections(a, b);
      setCommon(rows);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Lỗi');
      setCommon([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employees.length) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employees.length]);

  return (
    <div className="card">
      <div className="card-title">Kết nối chung (bạn chung)</div>
      <p className="card-desc">
        Những người cùng kết nối 1 hop với cả hai nhân viên (Knows / ReportsTo / WorksOn) — tương đương truy vấn graph Q4.
      </p>
      <div className="form-row">
        <div className="field">
          <label>Nhân viên A</label>
          <select value={a} onChange={(e) => setA(+e.target.value)}>
            {employees.map((e) => (
              <option key={e.employee_id} value={e.employee_id}>
                {e.full_name} — {e.title || ''}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Nhân viên B</label>
          <select value={b} onChange={(e) => setB(+e.target.value)}>
            {employees.map((e) => (
              <option key={e.employee_id} value={e.employee_id}>
                {e.full_name} — {e.title || ''}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ maxWidth: 140, display: 'flex', alignItems: 'flex-end' }}>
          <button type="button" className="btn btn-primary" disabled={loading} onClick={run} style={{ width: '100%' }}>
            {loading ? '…' : 'Tìm bạn chung'}
          </button>
        </div>
      </div>
      {err && <div className="alert alert-err">{err}</div>}
      {!err && common.length === 0 && !loading && (
        <div className="alert alert-info">Không có kết nối chung trong 1 hop.</div>
      )}
      {common.length > 0 && (
        <>
          <div className="meta-row">
            <div className="meta-pill">Số người chung: <strong>{common.length}</strong></div>
          </div>
          <div className="emp-grid" style={{ marginTop: 12 }}>
            {common.map((e) => (
              <div key={e.employee_id} className="emp-card" onClick={() => onSelectEmp(e.employee_id)}>
                <div className="av">
                  {e.full_name.split(' ').slice(-2).map((w) => w[0]).join('')}
                </div>
                <div className="nm">{e.full_name}</div>
                <div className="mt">{e.title || '—'}</div>
                <div className="mt">ID: {e.employee_id}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export const CommonPage = memo(CommonPageInner);

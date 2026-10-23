import { memo, useEffect, useState } from 'react';
import { api, type Employee } from '../api/client';
import { useAuth } from '../auth/AuthContext';


type Props = { employeeId: number; onChangeEmp: (id: number) => void };

function DetailPageInner({ employeeId, onChangeEmp }: Props) {
  const { user, can } = useAuth();
  const role = user!.role;
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [emp, setEmp] = useState<Employee | null>(null);
  const [connections, setConnections] = useState<
    (Employee & { relation?: string; relation_type?: string })[]
  >([]);
  const [managers, setManagers] = useState<Employee[]>([]);
  const [stats, setStats] = useState<{ summary?: string; total_connections?: number } | null>(null);
  const [toConn, setToConn] = useState<number>(0);
  const [connType, setConnType] = useState('COLLEAGUE');
  const [connMsg, setConnMsg] = useState('');
  const [degree, setDegree] = useState<{ out_degree?: number; in_degree?: number; by_type?: Record<string, number> } | null>(null);


  useEffect(() => {
    api.employees().then(setEmployees).catch(() => {});
  }, []);

  useEffect(() => {
    api.employee(employeeId).then(setEmp).catch(() => setEmp(null));
    api.connections(employeeId).then(setConnections).catch(() => setConnections([]));
    api.managers(employeeId).then(setManagers).catch(() => setManagers([]));
    api.stats(employeeId).then(setStats).catch(() => setStats(null));
    api.nodeDegree(employeeId).then(setDegree).catch(() => setDegree(null));
  }, [employeeId]);

  const tagClass = (t?: string) =>
    t === 'ReportsTo' ? 'tag-rt' : t === 'WorksOn' ? 'tag-wo' : 'tag-kn';

  return (
    <>
      <div className="page-eyebrow">Directory · Node</div>
      <h2 className="page-title">Employee detail</h2>
      <p className="page-lede">Profile, direct edges, managers, and degree readout.</p>
      <div className="card">
        <div className="field" style={{ maxWidth: 360 }}>
          <label>Chọn nhân viên</label>
          <select value={employeeId} onChange={(e) => onChangeEmp(+e.target.value)}>
            {employees.map((e) => (
              <option key={e.employee_id} value={e.employee_id}>
                {e.full_name} — {e.title || ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {emp && (
        <>
          <div className="grid-3" style={{ marginTop: 16 }}>
            <div className="stat">
              <div className="label">Kết nối trực tiếp</div>
              <div className="value">{connections.length}</div>
            </div>
            <div className="stat">
              <div className="label">Cấp trên</div>
              <div className="value">{managers.length}</div>
            </div>
            <div className="stat">
              <div className="label">Degree</div>
              <div className="value">{degree ? (degree.out_degree ?? 0) + (degree.in_degree ?? 0) : '—'}</div>
              <div className="hint">
                out {degree?.out_degree ?? '—'} · in {degree?.in_degree ?? '—'}
              </div>
            </div>
          </div>
          {degree?.by_type && (
            <div className="meta-row" style={{ marginTop: 10 }}>
              {Object.entries(degree.by_type).map(([k, v]) => (
                <div key={k} className="meta-pill">
                  {k} <strong>{v}</strong>
                </div>
              ))}
            </div>
          )}

          <div className="grid-2" style={{ marginTop: 16 }}>
            <div className="card">
              <div className="card-title" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                <span>{emp.full_name}</span>
                <span style={{ display: 'flex', gap: 6 }}>
                  {can.canEditEmployee(role) && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={async () => {
                        const name = prompt('Họ tên mới', emp.full_name);
                        if (!name || !name.trim()) return;
                        try {
                          const u = await api.updateEmployee(employeeId, { full_name: name.trim() });
                          setEmp(u);
                        } catch (e) {
                          alert(e instanceof Error ? e.message : 'Sửa thất bại');
                        }
                      }}
                    >
                      Sửa tên
                    </button>
                  )}
                  {can.canDeleteEmployee(role) && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={async () => {
                        if (!confirm(`Xóa ${emp.full_name}?`)) return;
                        try {
                          await api.deleteEmployee(employeeId);
                          alert('Đã xóa. Chọn nhân viên khác.');
                          setEmp(null);
                        } catch (e) {
                          alert(e instanceof Error ? e.message : 'Xóa thất bại');
                        }
                      }}
                    >
                      Xóa
                    </button>
                  )}
                </span>
              </div>
              <p className="card-desc">
                {emp.title} · {emp.department_name || 'N/A'} · ID {emp.employee_id}
              </p>
              <div className="card-title" style={{ marginTop: 8 }}>
                Chuỗi quản lý ↑
              </div>
              <ul className="list">
                {managers.length === 0 && (
                  <li style={{ color: 'var(--muted)' }}>Không có (cấp cao nhất)</li>
                )}
                {managers.map((m, i) => (
                  <li key={m.employee_id}>
                    <span>
                      {'　'.repeat(i)}↑ {m.full_name}
                    </span>
                    <span style={{ color: 'var(--muted)', fontSize: 12 }}>{m.title}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <div className="card-title">Kết nối trực tiếp</div>
              <ul className="list">
                {connections.length === 0 && (
                  <li style={{ color: 'var(--muted)' }}>Không có</li>
                )}
                {connections.map((c) => (
                  <li key={c.employee_id}>
                    <span>{c.full_name}</span>
                    <span className={`tag ${tagClass(c.relation_type)}`}>
                      {c.relation || c.relation_type || '—'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}

      {emp && employees.length > 0 && can.canCreateConnection(role) && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Tạo quan hệ Knows</div>
          <p className="card-desc">
            Gọi package <code>pkg_social_network.create_connection</code> (Oracle) hoặc báo 501 ở chế độ MOCK.
          </p>
          <div className="form-row">
            <div className="field">
              <label>Đến nhân viên</label>
              <select value={toConn || ''} onChange={(e) => setToConn(+e.target.value)}>
                <option value="">— Chọn —</option>
                {employees
                  .filter((e) => e.employee_id !== employeeId)
                  .map((e) => (
                    <option key={e.employee_id} value={e.employee_id}>
                      {e.full_name}
                    </option>
                  ))}
              </select>
            </div>
            <div className="field" style={{ maxWidth: 160 }}>
              <label>Loại</label>
              <select value={connType} onChange={(e) => setConnType(e.target.value)}>
                {['COLLEAGUE', 'FRIEND', 'MENTOR', 'MENTEE', 'TEAMMATE', 'FOLLOW'].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="field" style={{ maxWidth: 140, display: 'flex', alignItems: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ width: '100%' }}
                onClick={async () => {
                  if (!toConn) return;
                  setConnMsg('');
                  try {
                    const r = await api.createConnection({
                      from_id: employeeId,
                      to_id: toConn,
                      connection_type: connType,
                    });
                    setConnMsg(r.message || 'Đã tạo quan hệ');
                    api.connections(employeeId).then(setConnections);
                  } catch (e) {
                    setConnMsg(e instanceof Error ? e.message : 'Lỗi');
                  }
                }}
              >
                Tạo
              </button>
            </div>
          </div>
          {connMsg && (
            <div className={`alert ${connMsg.includes('Lỗi') || connMsg.includes('501') || connMsg.includes('MOCK') ? 'alert-info' : 'alert-ok'}`}>
              {connMsg}
            </div>
          )}
        </div>
      )}

    </>
  );
}

export const DetailPage = memo(DetailPageInner);

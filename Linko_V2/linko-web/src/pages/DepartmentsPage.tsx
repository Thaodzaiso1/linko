import { memo, useEffect, useState } from 'react';
import { api, type Employee } from '../api/client';

type Dept = { department_id: number; department_name: string; location?: string };

type Props = { onSelectEmp: (id: number) => void };

function DepartmentsPageInner({ onSelectEmp }: Props) {
  const [depts, setDepts] = useState<Dept[]>([]);
  const [emps, setEmps] = useState<Employee[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    Promise.all([api.departments(), api.employees()])
      .then(([d, e]) => {
        setDepts(d as Dept[]);
        setEmps(e);
        if (d.length) setActive((d as Dept[])[0].department_id);
      })
      .catch(() => setErr('Không tải được dữ liệu phòng ban'));
  }, []);

  const members = active
    ? emps.filter((e) => e.department_id === active)
    : [];

  const activeDept = depts.find((d) => d.department_id === active);

  return (
    <div className="grid-2">
      <div className="card">
        <div className="card-title">Danh sách phòng ban</div>
        {err && <div className="alert alert-err">{err}</div>}
        <ul className="list">
          {depts.map((d) => {
            const count = emps.filter((e) => e.department_id === d.department_id).length;
            return (
              <li
                key={d.department_id}
                style={{
                  cursor: 'pointer',
                  background: active === d.department_id ? 'var(--primary-soft)' : undefined,
                  margin: '0 -8px',
                  padding: '10px 8px',
                  borderRadius: 8,
                }}
                onClick={() => setActive(d.department_id)}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{d.department_name}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{d.location || '—'}</div>
                </div>
                <span className="tag tag-kn">{count} NV</span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="card">
        <div className="card-title">
          {activeDept ? activeDept.department_name : 'Nhân viên'}
        </div>
        <p className="card-desc">
          {activeDept?.location || 'Chọn phòng ban bên trái'} · {members.length} người
        </p>
        {members.length === 0 && <div className="empty">Không có nhân viên trong mẫu</div>}
        <div className="emp-grid">
          {members.map((e) => (
            <div key={e.employee_id} className="emp-card" onClick={() => onSelectEmp(e.employee_id)}>
              <div className="av">
                {e.full_name
                  .split(' ')
                  .slice(-2)
                  .map((w) => w[0])
                  .join('')}
              </div>
              <div className="nm">{e.full_name}</div>
              <div className="mt">{e.title || '—'}</div>
              <div className="mt">ID: {e.employee_id}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export const DepartmentsPage = memo(DepartmentsPageInner);

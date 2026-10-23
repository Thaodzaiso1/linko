import { memo, useEffect, useState } from 'react';
import { api, type Employee } from '../api/client';

type Project = {
  project_id: number;
  project_name: string;
  status?: string;
  department_id?: number;
};

type Props = { onSelectEmp: (id: number) => void };

function ProjectsPageInner({ onSelectEmp }: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [members, setMembers] = useState<(Employee & { role?: string; project_hint?: string })[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.projects()
      .then((p) => {
        setProjects(p as Project[]);
        if ((p as Project[]).length) setActive((p as Project[])[0].project_id);
      })
      .catch(() => setErr('Không tải được dự án'));
  }, []);

  useEffect(() => {
    if (active == null) return;
    api.projectMembers(active).then(setMembers).catch(() => setMembers([]));
  }, [active]);

  const cur = projects.find((p) => p.project_id === active);

  return (
    <div className="grid-2">
      <div className="card">
        <div className="card-title">Danh sách dự án</div>
        {err && <div className="alert alert-err">{err}</div>}
        <ul className="list">
          {projects.map((p) => (
            <li
              key={p.project_id}
              style={{
                cursor: 'pointer',
                background: active === p.project_id ? 'var(--primary-soft)' : undefined,
                margin: '0 -8px',
                padding: '10px 8px',
                borderRadius: 8,
              }}
              onClick={() => setActive(p.project_id)}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{p.project_name}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>ID {p.project_id}</div>
              </div>
              <span className={`tag ${p.status === 'ACTIVE' ? 'tag-wo' : 'tag-kn'}`}>
                {p.status || '—'}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <div className="card-title">{cur?.project_name || 'Thành viên'}</div>
        <p className="card-desc">
          Đồng đội qua cạnh WorksOn · {members.length} người
        </p>
        {members.length === 0 && <div className="empty">Chưa có thành viên trong mẫu</div>}
        <div className="emp-grid">
          {members.map((e) => (
            <div key={e.employee_id} className="emp-card" onClick={() => onSelectEmp(e.employee_id)}>
              <div className="av">
                {e.full_name.split(' ').slice(-2).map((w) => w[0]).join('')}
              </div>
              <div className="nm">{e.full_name}</div>
              <div className="mt">{e.title || '—'}</div>
              <div className="mt">{e.project_hint || e.role || ''}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export const ProjectsPage = memo(ProjectsPageInner);

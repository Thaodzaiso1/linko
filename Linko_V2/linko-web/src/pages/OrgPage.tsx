import { memo, useEffect, useState } from 'react';
import { api } from '../api/client';

type OrgNode = {
  employee_id: number;
  full_name: string;
  title?: string;
  department_name?: string;
  children?: OrgNode[];
  depth?: number;
};

type Props = { onSelectEmp: (id: number) => void };

function Node({ n, onSelect }: { n: OrgNode; onSelect: (id: number) => void }) {
  const [open, setOpen] = useState((n.depth || 0) < 2);
  const has = (n.children?.length || 0) > 0;
  return (
    <div className="org-node" style={{ marginLeft: (n.depth || 0) * 16 }}>
      <div className="org-row" onClick={() => onSelect(n.employee_id)}>
        {has ? (
          <button
            type="button"
            className="org-toggle"
            onClick={(e) => {
              e.stopPropagation();
              setOpen((o) => !o);
            }}
          >
            {open ? '▾' : '▸'}
          </button>
        ) : (
          <span className="org-toggle ghost">·</span>
        )}
        <span className="org-name">{n.full_name}</span>
        <span className="org-title">{n.title}</span>
        {n.department_name && <span className="tag tag-kn">{n.department_name}</span>}
      </div>
      {open && has && n.children!.map((c) => <Node key={c.employee_id} n={c} onSelect={onSelect} />)}
    </div>
  );
}

function OrgPageInner({ onSelectEmp }: Props) {
  const [trees, setTrees] = useState<OrgNode[]>([]);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .orgTree()
      .then((r) => setTrees(r.trees || []))
      .catch((e) => setErr(e instanceof Error ? e.message : 'Lỗi'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="card-title">Cây tổ chức (ReportsTo)</div>
      <p className="card-desc">
        Xây từ cạnh ReportsTo. Bấm tên để xem chi tiết NV. Mở/đóng nhánh bằng ▸.
      </p>
      {loading && <div className="empty">Đang tải…</div>}
      {err && <div className="alert alert-err">{err}</div>}
      {!loading && !trees.length && <div className="empty">Không có dữ liệu cây</div>}
      {trees.map((t) => (
        <div key={t.employee_id} className="org-tree">
          <Node n={t} onSelect={onSelectEmp} />
        </div>
      ))}
    </div>
  );
}

export const OrgPage = memo(OrgPageInner);

import { memo, useCallback, useEffect, useMemo, useState, type MouseEvent } from 'react';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { api, type Employee } from '../api/client';
import { toast } from '../components/Toast';
import { useAuth } from '../auth/AuthContext';
import { VirtualGrid } from '../components/VirtualGrid';

type Props = { onSelect: (id: number) => void; initialQuery?: string };

type Dept = { department_id: number; department_name: string };

type FormState = {
  full_name: string;
  email: string;
  title: string;
  department_id: number;
};

const emptyForm = (): FormState => ({
  full_name: '',
  email: '',
  title: 'Nhân viên',
  department_id: 1,
});



type EmpCardProps = {
  employee: Employee;
  query: string;
  canEdit: boolean;
  canDelete: boolean;
  deleting: boolean;
  onSelect: (id: number) => void;
  onEdit: (e: Employee, ev: MouseEvent) => void;
  onDelete: (e: Employee, ev: MouseEvent) => void;
};

function empCardAreEqual(prev: EmpCardProps, next: EmpCardProps): boolean {
  return (
    prev.employee.employee_id === next.employee.employee_id &&
    prev.employee.full_name === next.employee.full_name &&
    prev.employee.title === next.employee.title &&
    prev.employee.email === next.employee.email &&
    prev.employee.department_name === next.employee.department_name &&
    prev.employee.department_id === next.employee.department_id &&
    prev.query === next.query &&
    prev.canEdit === next.canEdit &&
    prev.canDelete === next.canDelete &&
    prev.deleting === next.deleting &&
    prev.onSelect === next.onSelect &&
    prev.onEdit === next.onEdit &&
    prev.onDelete === next.onDelete
  );
}

const EmpCard = memo(function EmpCard({
  employee: e,
  query,
  canEdit,
  canDelete,
  deleting,
  onSelect,
  onEdit,
  onDelete,
}: EmpCardProps) {
  const initials = e.full_name
    .split(' ')
    .slice(-2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  const highlight = (text: string) => {
    const qq = query.trim();
    if (!qq) return text;
    try {
      const parts = text.split(new RegExp(`(${qq.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
      return parts.map((p, i) =>
        p.toLowerCase() === qq.toLowerCase() ? (
          <mark key={i} className="hl">
            {p}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        )
      );
    } catch {
      return text;
    }
  };

  return (
    <div className="emp-card" onClick={() => onSelect(e.employee_id)}>
      <div className="av">{initials}</div>
      <div className="nm">{highlight(e.full_name)}</div>
      <div className="mt">
        {e.title || '—'} · {e.department_name || 'N/A'}
      </div>
      <div className="mt">
        ID: {e.employee_id}
        {e.email ? ` · ${e.email}` : ''}
      </div>
      <div className="emp-actions">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={(ev) => {
            ev.stopPropagation();
            onSelect(e.employee_id);
          }}
        >
          Chi tiết
        </button>
        {canEdit && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={(ev) => onEdit(e, ev)}>
            Sửa
          </button>
        )}
        {canDelete && (
          <button
            type="button"
            className="btn btn-danger btn-sm"
            disabled={deleting}
            onClick={(ev) => onDelete(e, ev)}
          >
            {deleting ? '…' : 'Xóa'}
          </button>
        )}
      </div>
    </div>
  );
}, empCardAreEqual);


function EmployeesPageInner({ onSelect, initialQuery = '' }: Props) {
  const { user, can } = useAuth();
  const role = user!.role;
  const [list, setList] = useState<Employee[]>([]);
  const [depts, setDepts] = useState<Dept[]>([]);
  const [q, setQ] = useState(initialQuery);
  const debouncedQ = useDebouncedValue(q, 300);
  const [submittedQ, setSubmittedQ] = useState(initialQuery);
  const [searched, setSearched] = useState(Boolean(initialQuery.trim()));
  const [dept, setDept] = useState('all');
  const [titleQ, setTitleQ] = useState('');
  const [sort, setSort] = useState<'name' | 'id' | 'title'>('name');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  const [modal, setModal] = useState<'create' | 'edit' | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState('');
  const [formOk, setFormOk] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.employees(), api.departments()])
      .then(([emps, d]) => {
        setList(emps);
        setDepts(d as Dept[]);
      })
      .catch(() => setErr('Không tải được danh sách nhân viên'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (initialQuery) {
      setQ(initialQuery);
      setSubmittedQ(initialQuery);
      setSearched(Boolean(initialQuery.trim()));
    }
  }, [initialQuery]);

  const runSearch = () => {
    setSubmittedQ(q);
    setSearched(true);
  };


  const departments = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of list) {
      map.set(String(e.department_id ?? 'na'), e.department_name || 'Khác');
    }
    for (const d of depts) {
      map.set(String(d.department_id), d.department_name);
    }
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1], 'vi'));
  }, [list, depts]);

  const titles = useMemo(() => {
    const s = new Set<string>();
    for (const e of list) {
      if (e.title) s.add(e.title);
    }
    return Array.from(s).sort((a, b) => a.localeCompare(b, 'vi'));
  }, [list]);

  const filtered = useMemo(() => {
    const qq = debouncedQ.trim().toLowerCase();
    const tq = titleQ.trim().toLowerCase();
    let rows = list.filter((e) => {
      if (dept !== 'all' && String(e.department_id ?? 'na') !== dept) return false;
      if (tq && !(e.title || '').toLowerCase().includes(tq)) return false;
      if (!qq) return true;
      const hay = [e.full_name, e.title || '', e.email || '', e.department_name || '', String(e.employee_id)]
        .join(' ')
        .toLowerCase();
      return qq.split(/\s+/).every((tok) => hay.includes(tok));
    });
    rows = [...rows].sort((a, b) => {
      if (sort === 'id') return a.employee_id - b.employee_id;
      if (sort === 'title') return (a.title || '').localeCompare(b.title || '', 'vi');
      return a.full_name.localeCompare(b.full_name, 'vi');
    });
    return rows;
  }, [list, debouncedQ, dept, titleQ, sort]);

  const initials = (name: string) =>
    name
      .split(' ')
      .slice(-2)
      .map((w) => w[0])
      .join('')
      .toUpperCase();

  const highlight = (text: string) => {
    const qq = q.trim();
    if (!qq) return text;
    try {
      const parts = text.split(new RegExp(`(${qq.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
      return parts.map((p, i) =>
        p.toLowerCase() === qq.toLowerCase() ? (
          <mark key={i} className="hl">
            {p}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        )
      );
    } catch {
      return text;
    }
  };

  const openCreate = () => {
    setForm({
      ...emptyForm(),
      department_id: depts[0]?.department_id || 1,
    });
    setEditId(null);
    setFormErr('');
    setFormOk('');
    setModal('create');
  };

  const openEdit = useCallback((e: Employee, ev: MouseEvent) => {
    ev.stopPropagation();
    setForm({
      full_name: e.full_name,
      email: e.email || '',
      title: e.title || 'Nhân viên',
      department_id: e.department_id || depts[0]?.department_id || 1,
    });
    setEditId(e.employee_id);
    setFormErr('');
    setFormOk('');
    setModal('edit');
  }, [depts]);

  const submitForm = async () => {
    setFormErr('');
    setFormOk('');
    if (!form.full_name.trim()) {
      setFormErr('Vui lòng nhập họ tên');
      return;
    }
    setSaving(true);
    const deptName = depts.find((d) => d.department_id === form.department_id)?.department_name;
    try {
      if (modal === 'create') {
        const created = await api.createEmployee({
          full_name: form.full_name.trim(),
          email: form.email.trim() || undefined,
          title: form.title.trim() || 'Nhân viên',
          department_id: form.department_id,
          department_name: deptName,
        });
        setFormOk(`Đã tạo ${created.full_name} (ID ${created.employee_id})`);
        toast('ok', `Đã tạo ${created.full_name}`);
        setList((prev) => [...prev, created]);
        setTimeout(() => {
          setModal(null);
          onSelect(created.employee_id);
        }, 600);
      } else if (modal === 'edit' && editId != null) {
        const updated = await api.updateEmployee(editId, {
          full_name: form.full_name.trim(),
          email: form.email.trim() || undefined,
          title: form.title.trim() || 'Nhân viên',
          department_id: form.department_id,
          department_name: deptName,
        });
        setFormOk('Đã cập nhật');
        toast('ok', 'Đã cập nhật nhân viên');
        setList((prev) => prev.map((x) => (x.employee_id === editId ? updated : x)));
        setTimeout(() => setModal(null), 500);
      }
    } catch (e) {
      setFormErr(e instanceof Error ? e.message : 'Thao tác thất bại');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = useCallback(async (e: Employee, ev: MouseEvent) => {
    ev.stopPropagation();
    if (!confirm(`Xóa nhân viên “${e.full_name}” (ID ${e.employee_id})?\nCác cạnh liên quan cũng sẽ bị gỡ (MOCK).`)) {
      return;
    }
    setDeletingId(e.employee_id);
    try {
      await api.deleteEmployee(e.employee_id);
      setList((prev) => prev.filter((x) => x.employee_id !== e.employee_id));
      toast('ok', `Đã xóa ${e.full_name}`);
    } catch (err) {
      toast('err', err instanceof Error ? err.message : 'Xóa thất bại');
    } finally {
      setDeletingId(null);
    }
  }, []);

  const canEditEmp = can.canEditEmployee(role);
  const canDeleteEmp = can.canDeleteEmployee(role);

  return (
    <>
      <div className="card">
        <div className="card-title" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <span>Tìm kiếm nhân viên</span>
          {can.canCreateEmployee(role) && (
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              + Tạo nhân viên
            </button>
          )}
        </div>
        <p className="card-desc">
          Tìm theo tên, email, chức danh, ID. Sửa / Xóa trực tiếp trên từng card.
        </p>

        <div className="form-row" style={{ alignItems: 'flex-end', marginBottom: 8 }}>
          <div className="field" style={{ flex: 2 }}>
            <label>Từ khóa</label>
            <input
              placeholder="Tên, email, chức danh, ID…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') runSearch();
              }}
              autoFocus
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={runSearch}>
            Tìm kiếm
          </button>
          {(q || dept !== 'all' || titleQ) && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setQ('');
                setSubmittedQ('');
                setSearched(false);
                setDept('all');
                setTitleQ('');
              }}
            >
              Xóa
            </button>
          )}
        </div>

        <div className="form-row" style={{ marginTop: 4 }}>
          <div className="field">
            <label>Phòng ban</label>
            <select value={dept} onChange={(e) => setDept(e.target.value)}>
              <option value="all">Tất cả phòng ban</option>
              {departments.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Chức danh</label>
            <select value={titleQ} onChange={(e) => setTitleQ(e.target.value)}>
              <option value="">Tất cả chức danh</option>
              {titles.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ maxWidth: 160 }}>
            <label>Sắp xếp</label>
            <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
              <option value="name">Theo tên</option>
              <option value="id">Theo ID</option>
              <option value="title">Theo chức danh</option>
            </select>
          </div>
        </div>

        {searched && submittedQ.trim() && (
          <div className="alert alert-info" style={{ marginTop: 8 }}>
            Kết quả tìm “<strong>{submittedQ.trim()}</strong>”: <strong>{filtered.length}</strong> nhân viên
            {filtered.length === 0 ? ' — không khớp' : ''}
          </div>
        )}
        <div className="meta-row">
          <div className="meta-pill">
            Hiển thị: <strong>{filtered.length}</strong> / {list.length}
          </div>
          {dept !== 'all' && (
            <div className="meta-pill">
              Phòng: <strong>{departments.find(([id]) => id === dept)?.[1] || dept}</strong>
            </div>
          )}
          {titleQ && (
            <div className="meta-pill">
              Chức danh: <strong>{titleQ}</strong>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          Kết quả
          <span className="meta-pill" style={{ marginLeft: 8, fontWeight: 500 }}>
            {filtered.length} mục
          </span>
        </div>
        {err && <div className="alert alert-err">{err}</div>}
        {loading && <div className="empty">Đang tải…</div>}
        {!loading && !err && filtered.length === 0 && (
          <div className="empty">
            Không tìm thấy nhân viên phù hợp{q.trim() ? ` với “${q.trim()}”` : ''}.
            <div style={{ marginTop: 10 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setQ(''); setSubmittedQ(''); setSearched(false); setDept('all'); setTitleQ(''); }}>
                Xóa bộ lọc
              </button>
            </div>
          </div>
        )}
        <VirtualGrid
          items={filtered}
          threshold={200}
          estimateItemHeight={168}
          minColumnWidth={228}
          gap={8}
          getKey={(e) => e.employee_id}
          renderItem={(e) => (
            <EmpCard
              employee={e}
              query={debouncedQ}
              canEdit={canEditEmp}
              canDelete={canDeleteEmp}
              deleting={deletingId === e.employee_id}
              onSelect={onSelect}
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          )}
        />
      </div>

      {modal && (
        <div className="modal-backdrop" onClick={() => !saving && setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modal === 'create' ? 'Tạo nhân viên mới' : `Sửa nhân viên #${editId}`}</h3>
            <p className="modal-desc">
              {modal === 'create'
                ? 'Thêm vertex Employee (MOCK / Oracle INSERT).'
                : 'Cập nhật thông tin nhân viên (PUT).'}
            </p>
            <div className="field-stack">
              <div className="field">
                <label>Họ và tên *</label>
                <input
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Nguyễn Văn A"
                  autoFocus
                />
              </div>
              <div className="field">
                <label>Email</label>
                <input
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="a.nguyen@company.vn"
                />
              </div>
              <div className="field">
                <label>Chức danh</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Nhân viên"
                />
              </div>
              <div className="field">
                <label>Phòng ban</label>
                <select
                  value={form.department_id}
                  onChange={(e) => setForm({ ...form, department_id: +e.target.value })}
                >
                  {(depts.length
                    ? depts
                    : departments.map(([id, name]) => ({
                        department_id: Number(id) || 1,
                        department_name: name,
                      }))
                  ).map((d) => (
                    <option key={d.department_id} value={d.department_id}>
                      {d.department_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {formErr && <div className="alert alert-err">{formErr}</div>}
            {formOk && <div className="alert alert-ok">{formOk}</div>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" disabled={saving} onClick={() => setModal(null)}>
                Hủy
              </button>
              <button type="button" className="btn btn-primary" disabled={saving} onClick={submitForm}>
                {saving ? 'Đang lưu…' : modal === 'create' ? 'Tạo nhân viên' : 'Lưu thay đổi'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export const EmployeesPage = memo(EmployeesPageInner);

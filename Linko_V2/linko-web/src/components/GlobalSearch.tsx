import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { api, type Employee } from '../api/client';

type Props = {
  onSelectEmp: (id: number) => void;
  onSearchAll?: (query: string) => void;
  onOpenEmployees?: (query: string) => void;
};

function GlobalSearchInner({ onSelectEmp, onSearchAll, onOpenEmployees }: Props) {
  const [q, setQ] = useState('');
  const debouncedQ = useDebouncedValue(q, 300);
  const [list, setList] = useState<Employee[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);

  const openAll = onSearchAll || onOpenEmployees || (() => {});

  useEffect(() => {
    api.employees().then(setList).catch(() => {});
  }, []);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const results = useMemo(() => {
    const qq = debouncedQ.trim().toLowerCase();
    if (!qq) return [];
    return list
      .filter((e) => {
        const hay = [e.full_name, e.title || '', e.email || '', e.department_name || '', String(e.employee_id)]
          .join(' ')
          .toLowerCase();
        return qq.split(/\s+/).every((tok) => hay.includes(tok));
      })
      .slice(0, 8);
  }, [list, debouncedQ]);

  const initials = (name: string) =>
    name
      .split(' ')
      .slice(-2)
      .map((w) => w[0])
      .join('')
      .toUpperCase();

  const go = (id: number) => {
    setOpen(false);
    setQ('');
    onSelectEmp(id);
  };

  const submitSearch = () => {
    const qq = q.trim();
    if (!qq) {
      setOpen(true);
      return;
    }
    setOpen(false);
    openAll(qq);
  };

  return (
    <div className="global-search" ref={box} style={{ display: 'flex', gap: 6, alignItems: 'center', width: 'auto' }}>
      <div style={{ position: 'relative', flex: 1, minWidth: 0, width: 'min(220px, 32vw)' }}>
        <input
          placeholder="Tìm nhân viên…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
            setActive(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setActive((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setActive((i) => Math.max(i - 1, 0));
            } else if (e.key === 'Enter') {
              e.preventDefault();
              if (results[active]) go(results[active].employee_id);
              else submitSearch();
            } else if (e.key === 'Escape') {
              setOpen(false);
            }
          }}
          style={{ width: '100%' }}
        />
        {open && q.trim() && (
          <div className="global-search-drop">
            <div
              className="global-search-footer"
              style={{ borderTop: 'none', borderBottom: '1px solid var(--border)' }}
            >
              {results.length} kết quả gợi ý
            </div>
            {results.length === 0 && (
              <div className="empty" style={{ padding: 14 }}>
                Không có kết quả — bấm Tìm để xem trang đầy đủ
              </div>
            )}
            {results.map((e, i) => (
              <button
                key={e.employee_id}
                type="button"
                className="global-search-item"
                style={i === active ? { background: 'var(--primary-soft)' } : undefined}
                onMouseEnter={() => setActive(i)}
                onClick={() => go(e.employee_id)}
              >
                <div className="gs-av">{initials(e.full_name)}</div>
                <div>
                  <div className="gs-name">{e.full_name}</div>
                  <div className="gs-sub">
                    {e.title || '—'} · {e.department_name || 'N/A'} · #{e.employee_id}
                  </div>
                </div>
              </button>
            ))}
            <div
              className="global-search-footer"
              onClick={submitSearch}
            >
              Tìm “{q.trim()}” trên trang Nhân viên →
            </div>
          </div>
        )}
      </div>
      <button type="button" className="btn btn-primary btn-sm" onClick={submitSearch} title="Tìm kiếm">
        Tìm
      </button>
    </div>
  );
}

export const GlobalSearch = memo(GlobalSearchInner);

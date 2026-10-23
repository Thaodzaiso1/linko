import { memo, useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { api, type Employee, type PathResult } from '../api/client';
import { loadHistory, pushHistory, clearHistory, type PathHistoryItem } from '../api/history';
import { toast } from '../components/Toast';

const QUICK: { label: string; from: number; to: number }[] = [
  { label: 'Junior BE → CEO', from: 20, to: 1 },
  { label: 'Dev HN → Dev DN', from: 53, to: 58 },
  { label: 'Senior BE → CEO', from: 9, to: 1 },
  { label: 'Junior BE → AI', from: 20, to: 64 },
  { label: 'Tech Lead → PM', from: 8, to: 23 },
];

type Props = { onSelectEmp: (id: number) => void };

function PathPageInner({ onSelectEmp }: Props) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [fromId, setFromId] = useState(20);
  const [toId, setToId] = useState(1);
  const [maxHops, setMaxHops] = useState(6);
  const [edgeTypes, setEdgeTypes] = useState<string[]>([]);
  const [kPaths, setKPaths] = useState<{ path_length: number; nodes: { employee_id: number; full_name: string }[] }[]>([]);
  const [kLoading, setKLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PathResult | null>(null);
  const [error, setError] = useState('');
  const [activeChip, setActiveChip] = useState(0);
  const [history, setHistory] = useState<PathHistoryItem[]>(() => loadHistory());
  const [autoRun, setAutoRun] = useState(false);
  const [autoIdx, setAutoIdx] = useState(0);
  const [autoDelay, setAutoDelay] = useState(3);
  const [autoLoop, setAutoLoop] = useState(0);
  const graphRef = useRef<HTMLDivElement>(null);
  const netRef = useRef<Network | null>(null);

  useEffect(() => {
    api.employees()
      .then((list) => {
        setEmployees(list);
        if (list.length && !list.some((e) => e.employee_id === fromId)) {
          setFromId(list[0].employee_id);
        }
      })
      .catch(() => setError('Không kết nối FastAPI (port 8000). Chạy: uvicorn main:app --port 8000'));
  }, []);

  useEffect(() => {
    if (!result?.found || !result.nodes || !result.steps || !graphRef.current) return;
    const nodes = result.nodes.map((n, i) => ({
      id: n.employee_id,
      label: n.full_name.split(' ').slice(-2).join(' '),
      title: `${n.full_name}\n${n.title || ''}`,
      color: i === 0 ? '#3b82f6' : i === result.nodes!.length - 1 ? '#059669' : '#8b5cf6',
      font: { color: '#fff', size: 13 },
    }));
    const edges = result.steps.map((s, i) => ({
      id: i,
      from: s.from_id,
      to: s.to_id,
      label: s.relation,
      arrows: 'to' as const,
      color: { color: '#64748b' },
      font: { color: '#94a3b8', size: 11 },
    }));
    if (netRef.current) netRef.current.destroy();
    netRef.current = new Network(
      graphRef.current,
      { nodes, edges },
      {
        layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', levelSeparation: 170 } },
        physics: false,
        edges: { smooth: { enabled: true, type: 'cubicBezier', roundness: 0.4 } },
        nodes: { shape: 'box', margin: { top: 12, right: 12, bottom: 12, left: 12 }, borderWidth: 0 },
        interaction: { hover: true },
      }
    );
  }, [result]);

  const run = async (f = fromId, t = toId) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data =
          edgeTypes.length > 0
            ? await api.shortestPathFiltered(f, t, maxHops, edgeTypes)
            : await api.shortestPath(f, t, maxHops);
      setResult(data);
      setKPaths([]);
      const fromE = employees.find((e) => e.employee_id === f);
      const toE = employees.find((e) => e.employee_id === t);
      pushHistory({
        from_id: f,
        to_id: t,
        from_name: data.from?.full_name || fromE?.full_name || String(f),
        to_name: data.to?.full_name || toE?.full_name || String(t),
        path_length: data.found ? (data.path_length ?? null) : null,
        found: !!data.found,
        at: new Date().toISOString(),
      });
      setHistory(loadHistory());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Lỗi tìm đường');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employees.length && sessionStorage.getItem('linko-autorun') === '1') {
      sessionStorage.removeItem('linko-autorun');
      setAutoRun(true);
      toast('ok', 'Bắt đầu demo tự động');
    }
  }, [employees.length]);

  useEffect(() => {
    if (employees.length) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employees.length]);

  // Chạy tự động liên tục: lặp vô hạn 5 kịch bản cho đến khi bấm Dừng
  useEffect(() => {
    if (!autoRun || !employees.length) return;
    let cancelled = false;
    let idx = 0;
    let loops = 0;
    let timer: number | undefined;

    const sleep = (ms: number) =>
      new Promise<void>((resolve) => {
        timer = window.setTimeout(resolve, ms);
      });

    const loop = async () => {
      setAutoLoop(0);
      while (!cancelled) {
        const q = QUICK[idx % QUICK.length];
        const step = idx % QUICK.length;
        setActiveChip(step);
        setFromId(q.from);
        setToId(q.to);
        setAutoIdx(step);
        try {
          await run(q.from, q.to);
        } catch {
          /* continue */
        }
        if (cancelled) break;
        idx += 1;
        if (idx % QUICK.length === 0) {
          loops += 1;
          setAutoLoop(loops);
          toast('info', `Hoàn thành vòng ${loops} — tiếp tục…`);
        }
        await sleep(Math.max(2000, autoDelay * 1000));
      }
    };

    void loop();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRun, autoDelay, employees.length]);


  const loadKPaths = async () => {
    setKLoading(true);
    try {
      const r = await api.kShortest(fromId, toId, 3);
      setKPaths(r.paths || []);
      toast('ok', `Found ${r.found} alternate paths`);
    } catch (e) {
      toast('err', e instanceof Error ? e.message : 'k-shortest failed');
    } finally {
      setKLoading(false);
    }
  };


  return (
    <>
      <div className="page-eyebrow">Graph · Query</div>
      <h2 className="page-title">Shortest path</h2>
      <p className="page-lede">BFS over ReportsTo, WorksOn, Knows. Auto-demo cycles sample pairs.</p>
      <div className="card">
        <div className="card-title">Query</div>
        <p className="card-desc">
          Chọn hai nhân viên. Hệ thống tìm chuỗi ngắn nhất qua <strong>ReportsTo</strong>,{' '}
          <strong>WorksOn</strong> và <strong>Knows</strong> (BFS / package PL/SQL + GRAPH_TABLE).
        </p>
        <div className="chips">
          {QUICK.map((q, i) => (
            <button
              key={q.label}
              type="button"
              className={`chip${activeChip === i ? ' active' : ''}`}
              onClick={() => {
                setAutoRun(false);
                setActiveChip(i);
                setFromId(q.from);
                setToId(q.to);
                run(q.from, q.to);
              }}
            >
              {q.label}
            </button>
          ))}
        </div>

        <div className="form-row" style={{ marginBottom: 12, alignItems: 'center' }}>
          <button
            type="button"
            className={`btn ${autoRun ? 'btn-danger' : 'btn-primary'}`}
            disabled={!employees.length}
            onClick={() => {
              if (autoRun) {
                setAutoRun(false);
                toast('info', 'Đã dừng chạy liên tục');
              } else {
                setAutoRun(true);
                toast('ok', 'Chạy liên tục — lặp 5 kịch bản demo');
              }
            }}
          >
            {autoRun ? '⏹ Dừng' : '▶ Chạy tự động liên tục'}
          </button>
          <div className="field" style={{ maxWidth: 120 }}>
            <label>Chu kỳ (giây)</label>
            <input
              type="number"
              min={2}
              max={15}
              value={autoDelay}
              disabled={autoRun}
              onChange={(e) => setAutoDelay(Math.max(2, +e.target.value || 3))}
            />
          </div>
          {autoRun && (
            <div className="meta-pill">
              🔄 Liên tục · <strong>{QUICK[autoIdx % QUICK.length]?.label}</strong>
              {' '}({(autoIdx % QUICK.length) + 1}/{QUICK.length})
              {autoLoop > 0 ? ` · vòng ${autoLoop}` : ''}
            </div>
          )}
        </div>
        <div className="form-row">
          <div className="field">
            <label>Nhân viên nguồn</label>
            <select value={fromId} onChange={(e) => { setFromId(+e.target.value); setActiveChip(-1); }}>
              {employees.map((e) => (
                <option key={e.employee_id} value={e.employee_id}>
                  {e.full_name} — {e.title || ''}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Nhân viên đích</label>
            <select value={toId} onChange={(e) => { setToId(+e.target.value); setActiveChip(-1); }}>
              {employees.map((e) => (
                <option key={e.employee_id} value={e.employee_id}>
                  {e.full_name} — {e.title || ''}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ maxWidth: 100 }}>
            <label>Max hops</label>
            <input type="number" min={1} max={12} value={maxHops} onChange={(e) => setMaxHops(+e.target.value || 6)} />
          </div>
          <div className="field" style={{ flex: '1 1 100%' }}>
            <label>Edge filter</label>
            <div className="chips" style={{ marginBottom: 0 }}>
              {(['ReportsTo', 'WorksOn', 'Knows'] as const).map((ty) => (
                <button
                  key={ty}
                  type="button"
                  className={`chip${edgeTypes.includes(ty) ? ' active' : ''}`}
                  onClick={() =>
                    setEdgeTypes((prev) =>
                      prev.includes(ty) ? prev.filter((x) => x !== ty) : [...prev, ty]
                    )
                  }
                >
                  {ty}
                </button>
              ))}
            </div>
          </div>
          <div className="field" style={{ maxWidth: 150, display: 'flex', alignItems: 'flex-end' }}>
            <button type="button" className="btn btn-primary" disabled={loading || !employees.length} onClick={() => run()} style={{ width: '100%' }}>
              {loading ? <span className="spinner" /> : null}
              {loading ? ' Đang tìm…' : 'Tìm đường'}
            </button>
          </div>
        </div>
        {error && <div className="alert alert-err">⚠ {error}</div>}
        {result && !result.found && (
          <div className="alert alert-err">❌ {result.message || 'Không tìm thấy đường'}</div>
        )}
        {result?.found && result.steps && (
          <>
            <div className="alert alert-ok" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <span>✅ Path length {result.path_length ?? '—'}</span>
              <button type="button" className="btn btn-ghost btn-sm" disabled={kLoading} onClick={loadKPaths}>
                {kLoading ? '…' : 'K-shortest (3)'}
              </button>
            </div>
            {kPaths.length > 0 && (
              <div className="card" style={{ marginTop: 10 }}>
                <div className="card-title">Alternate paths</div>
                <ul className="list">
                  {kPaths.map((path, i) => (
                    <li key={i}>
                      <span>
                        #{i + 1} · len <strong>{path.path_length}</strong>
                        {' · '}
                        {path.nodes?.map((n) => n.full_name).join(' → ')}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="meta-row">
              <div className="meta-pill">Số bước: <strong>{result.path_length}</strong></div>
              {result.from && <div className="meta-pill">Từ: <strong>{result.from.full_name}</strong></div>}
              {result.to && <div className="meta-pill">Đến: <strong>{result.to.full_name}</strong></div>}
            </div>
            <div className="path-flow">
              {result.steps.map((s, i) => (
                <span key={i} style={{ display: 'contents' }}>
                  <div className={`path-node${i === 0 ? ' start' : ''}`} onClick={() => onSelectEmp(s.from_id)}>
                    <div className="n">{s.from_name}</div>
                    <div className="t">{s.from_title}</div>
                  </div>
                  <div className="path-arrow"><span>→</span>{s.relation}</div>
                  {i === result.steps!.length - 1 && (
                    <div className="path-node end" onClick={() => onSelectEmp(s.to_id)}>
                      <div className="n">{s.to_name}</div>
                      <div className="t">{s.to_title}</div>
                    </div>
                  )}
                </span>
              ))}
            </div>
          </>
        )}
      </div>
      {result?.found && (
        <div className="card">
          <div className="card-title">Sơ đồ đường đi</div>
          <p className="card-desc">Xanh dương = nguồn · Tím = trung gian · Xanh lá = đích</p>
          <div className="graph-box" ref={graphRef} />
        </div>
      )}

      {result?.found && result.steps && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => {
              const lines = [
                `Linko — Đường ngắn nhất (${result.path_length} bước)`,
                `Từ: ${result.from?.full_name}`,
                `Đến: ${result.to?.full_name}`,
                '',
                ...result.steps!.map(
                  (s, i) => `${i + 1}. ${s.from_name} —[${s.relation}]→ ${s.to_name}`
                ),
              ];
              navigator.clipboard?.writeText(lines.join('\n'));
              toast('ok', 'Đã copy đường đi vào clipboard');
            }}
          >
            📋 Copy đường đi
          </button>
        </div>
      )}

      {history.length > 0 && (
        <div className="card">
          <div className="card-title" style={{ justifyContent: 'space-between' }}>
            <span>Lịch sử tìm đường</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => { clearHistory(); setHistory([]); }}>
              Xóa lịch sử
            </button>
          </div>
          <ul className="list">
            {history.map((h, i) => (
              <li key={i} style={{ cursor: 'pointer' }} onClick={() => { setFromId(h.from_id); setToId(h.to_id); setActiveChip(-1); run(h.from_id, h.to_id); }}>
                <span>
                  {h.from_name} → {h.to_name}
                  <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 8 }}>
                    {h.found ? `${h.path_length} bước` : 'không có đường'}
                  </span>
                </span>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                  {new Date(h.at).toLocaleString('vi-VN')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

    </>
  );
}

export const PathPage = memo(PathPageInner);

import { memo, useEffect, useState } from 'react';
import { api, type Employee } from '../api/client';

type Props = { onSelectEmp: (id: number) => void };

function InsightsPageInner({ onSelectEmp }: Props) {
  const [ranking, setRanking] = useState<(Employee & { degree: number; rank: number })[]>([]);
  const [comps, setComps] = useState<{ size: number; members: string[] }[]>([]);
  const [diam, setDiam] = useState<{
    estimated_diameter: number;
    pair: { from_name: string; to_name: string; from_id: number; to_id: number } | null;
  } | null>(null);
  const [centerId, setCenterId] = useState(8);
  const [depth, setDepth] = useState(1);
  const [nbh, setNbh] = useState<{ node_count: number; edge_count: number; nodes: Employee[] } | null>(
    null
  );
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.centrality(12), api.components(), api.diameter(10)])
      .then(([c, co, d]) => {
        setRanking(c.ranking || []);
        setComps(co.components || []);
        setDiam(d);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : 'Load failed'))
      .finally(() => setLoading(false));
  }, []);

  const loadNbh = async () => {
    try {
      const r = await api.neighborhood(centerId, depth);
      setNbh(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Neighborhood failed');
    }
  };

  return (
    <>
      <div className="page-eyebrow">Graph · Analytics</div>
      <h2 className="page-title">Network insights</h2>
      <p className="page-lede">
        Degree centrality, connected components, diameter estimate, and ego-neighborhood from API
        v3.
      </p>

      {err && <div className="alert alert-err">{err}</div>}
      {loading && <div className="empty">Loading metrics…</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Degree centrality</div>
          <p className="card-desc">Top nodes by edge count (influence proxy).</p>
          <ul className="list">
            {ranking.map((r) => (
              <li key={r.employee_id} style={{ cursor: 'pointer' }} onClick={() => onSelectEmp(r.employee_id)}>
                <span>
                  <span className="meta-pill" style={{ marginRight: 8 }}>
                    #{r.rank}
                  </span>
                  <strong>{r.full_name}</strong>
                  <span style={{ color: 'var(--muted)', marginLeft: 6 }}>{r.title}</span>
                </span>
                <span className="tag tag-wo">deg {r.degree}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <div className="card-title">Components & diameter</div>
          <p className="card-desc">Undirected connectivity snapshot.</p>
          {diam && (
            <div className="meta-row">
              <div className="meta-pill">
                Diameter ~ <strong>{diam.estimated_diameter}</strong>
              </div>
              {diam.pair && (
                <div className="meta-pill">
                  Far pair: {diam.pair.from_name} → {diam.pair.to_name}
                </div>
              )}
            </div>
          )}
          <ul className="list">
            {comps.map((c, i) => (
              <li key={i}>
                <span>
                  Component {i + 1} · size <strong>{c.size}</strong>
                </span>
                <span style={{ fontSize: 11, color: 'var(--muted)', maxWidth: '50%', textAlign: 'right' }}>
                  {c.members?.slice(0, 4).join(', ')}
                  {(c.members?.length || 0) > 4 ? '…' : ''}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-title">Ego neighborhood</div>
        <p className="card-desc">Nodes and edges within depth of a center employee.</p>
        <div className="form-row">
          <div className="field">
            <label>Center ID</label>
            <input type="number" value={centerId} onChange={(e) => setCenterId(+e.target.value || 1)} />
          </div>
          <div className="field">
            <label>Depth</label>
            <input type="number" min={1} max={4} value={depth} onChange={(e) => setDepth(+e.target.value || 1)} />
          </div>
          <button type="button" className="btn btn-primary" onClick={loadNbh}>
            Load neighborhood
          </button>
        </div>
        {nbh && (
          <>
            <div className="meta-row">
              <div className="meta-pill">
                Nodes <strong>{nbh.node_count}</strong>
              </div>
              <div className="meta-pill">
                Edges <strong>{nbh.edge_count}</strong>
              </div>
            </div>
            <div className="emp-grid" style={{ marginTop: 10 }}>
              {nbh.nodes.map((n) => (
                <div key={n.employee_id} className="emp-card" onClick={() => onSelectEmp(n.employee_id)}>
                  <div className="nm">{n.full_name}</div>
                  <div className="mt">{n.title}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}

export const InsightsPage = memo(InsightsPageInner);

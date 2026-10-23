import { memo, useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { api } from '../api/client';
import { Icon } from '../components/Icon';

function GraphPageInner() {
  const ref = useRef<HTMLDivElement>(null);
  const net = useRef<Network | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({ nodes: 0, edges: 0 });
  const [physics, setPhysics] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.graphOverview(50).then(data => {
      if (cancelled || !ref.current) return;
      const nodes = data.nodes.map(n => ({
        ...n,
        group: n.group === undefined ? undefined : String(n.group),
        color: {
          background: n.group === 2 ? '#7f8cfa' : n.group === 1 ? '#b59cff' : n.group === 12 ? '#67d8c1' : '#f2b37e',
          border: '#ffffff', highlight: { background: '#fff', border: '#bca7ff' },
        },
        font: { color: '#e5e6fa', size: 12, face: 'Inter, sans-serif' },
      }));
      net.current?.destroy();
      net.current = new Network(ref.current, { nodes, edges: data.edges }, {
        autoResize: true,
        interaction: { hover: true, tooltipDelay: 160, navigationButtons: false, keyboard: true },
        physics: { enabled: physics, barnesHut: { gravitationalConstant: -3400, springLength: 115, springConstant: .03 }, stabilization: { iterations: 150 } },
        edges: { smooth: { enabled: true, type: 'dynamic', roundness: .3 }, color: { color: '#5e688f', highlight: '#a99bff', opacity: .7 }, font: { size: 9, color: '#9da7d3', strokeWidth: 0 }, width: 1.5 },
        nodes: { shape: 'dot', size: 19, borderWidth: 2, shadow: { enabled: true, color: '#10102655', size: 10, x: 0, y: 4 } },
      });
      setCounts({ nodes: data.nodes.length, edges: data.edges.length });
      setLoading(false);
    }).catch(e => { if (!cancelled) { setErr(e instanceof Error ? e.message : 'Không tải được đồ thị'); setLoading(false); } });
    return () => { cancelled = true; net.current?.destroy(); net.current = null; };
  }, []);

  const togglePhysics = () => {
    const next = !physics;
    setPhysics(next);
    net.current?.setOptions({ physics: { enabled: next } });
  };

  return <div className="network-page">
    <div className="network-intro"><div><span className="page-eyebrow">NETWORK EXPLORER</span><h2 className="page-title">Bản đồ kết nối thông minh</h2><p className="page-lede">Kéo thả để di chuyển, cuộn để phóng to và nhấp vào một nút để khám phá mạng lưới nhân sự.</p></div><div className="network-counts"><span><strong>{counts.nodes}</strong> nút</span><span><strong>{counts.edges}</strong> cạnh</span></div></div>
    <div className="network-panel">
      <div className="network-toolbar"><div className="network-toolbar-label"><Icon name="network" size={18}/><span>Organization Network</span><i/></div><div className="network-toolbar-actions"><button type="button" onClick={() => net.current?.fit({animation:{duration:350,easingFunction:'easeInOutQuad'}})}><Icon name="target" size={16}/> Vừa khung</button><button type="button" onClick={togglePhysics}><Icon name="activity" size={16}/>{physics?'Cố định nút':'Bật chuyển động'}</button></div></div>
      <div className="graph-box" ref={ref}/>
      {loading && <div className="network-loading"><span className="spinner"/> Đang dựng đồ thị...</div>}
      {err && <div className="alert alert-err">{err}</div>}
      <div className="network-legend"><span><i className="dot-purple"/> Ban lãnh đạo</span><span><i className="dot-blue"/> Công nghệ</span><span><i className="dot-green"/> R&amp;D</span><span><i className="dot-orange"/> Bộ phận khác</span><small>Đồ thị lấy từ API /api/graph/overview</small></div>
    </div>
  </div>;
}

export const GraphPage = memo(GraphPageInner);

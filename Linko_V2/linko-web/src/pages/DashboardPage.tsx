import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import type { PageId } from '../app/App';
import { api, type DashboardOverview } from '../api/client';
import { Icon, type IconName } from '../components/Icon';

type Props = { onNavigate: (p: PageId) => void; onSelectEmp?: (id: number) => void };
const colors = ['#1677ff', '#8b5cf6', '#17b7a4', '#f5a524', '#ee6c92', '#586fe4'];
const relationshipColors = ['#1877f2', '#9061f9', '#22b8a3', '#ffad49', '#ed7193'];
const fmt = (n: number | undefined) => n == null ? '—' : new Intl.NumberFormat('vi-VN').format(n);
const initials = (name: string) => name.trim().split(/\s+/).slice(-2).map(x => x[0]).join('').toUpperCase();

const ConnectionsIllustration = memo(function ConnectionsIllustration() {
  const nodes = [
    { x: 66, y: 139, r: 21, label: 'NH', tone: 'a' },
    { x: 178, y: 55, r: 24, label: 'MT', tone: 'b' },
    { x: 172, y: 217, r: 27, label: 'AL', tone: 'c' },
    { x: 293, y: 127, r: 36, label: 'LK', tone: 'main' },
    { x: 413, y: 51, r: 21, label: 'TN', tone: 'd' },
    { x: 426, y: 228, r: 27, label: 'HP', tone: 'e' },
  ];
  const edges = [[0,1],[0,2],[0,3],[1,3],[1,4],[2,3],[2,5],[3,4],[3,5],[4,5]];
  return <svg className="social-network-svg" viewBox="0 0 500 282" fill="none" role="img" aria-label="Minh họa mạng lưới đồng nghiệp">
    <defs>
      <linearGradient id="line-gradient" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#5d93ff" stopOpacity=".6"/><stop offset="1" stopColor="#96e3d9" stopOpacity=".85"/></linearGradient>
    </defs>
    <circle cx="267" cy="135" r="116" stroke="white" strokeOpacity=".16" strokeDasharray="5 8"/>
    <circle cx="267" cy="135" r="82" stroke="white" strokeOpacity=".12"/>
    {edges.map(([a,b],i) => <line key={i} x1={nodes[a].x} y1={nodes[a].y} x2={nodes[b].x} y2={nodes[b].y} stroke="url(#line-gradient)" strokeWidth="1.75" strokeDasharray={i % 3 === 0 ? '5 6' : undefined}/>)}
    {nodes.map((node,i) => <g key={i}>
      <circle cx={node.x} cy={node.y} r={node.r+7} fill="white" fillOpacity=".12"/>
      <circle cx={node.x} cy={node.y} r={node.r} fill={node.tone==='main' ? '#ffffff' : ['#eac2e0','#c3eafa','#ffdac3','#fff','#c9c8ff','#b7f0e4'][i]} stroke="white" strokeWidth="3"/>
      <text x={node.x} y={node.y+4} fill={node.tone==='main' ? '#2362cc' : '#25426d'} textAnchor="middle" fontSize={node.tone==='main' ? 16 : 11} fontWeight="800" fontFamily="Inter, system-ui">{node.label}</text>
    </g>)}
    <g transform="translate(305 184)"><rect width="152" height="40" rx="18" fill="white"/><circle cx="23" cy="20" r="10" fill="#d9f9ee"/><path d="m18 20 3 3 6-6" stroke="#12a58f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><text x="41" y="17" fill="#153362" fontSize="10" fontWeight="750">Mạng lưới kết nối</text><text x="41" y="29" fill="#8290a8" fontSize="9">Cùng phát triển mỗi ngày</text></g>
  </svg>;
});

function DashboardPageInner({ onNavigate, onSelectEmp }: Props) {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloading, setReloading] = useState(false);
  const load = useCallback(async (refresh = false) => {
    if (refresh) setReloading(true); else setLoading(true);
    setError('');
    try { setData(await api.dashboardOverview()); }
    catch (err) { setError(err instanceof Error ? err.message : 'Không thể tải dữ liệu tổng quan'); }
    finally { setLoading(false); setReloading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const total = data?.relationships.reduce((sum, item) => sum + item.count, 0) ?? 0;
  const donut = useMemo(() => {
    if (!total || !data?.relationships.length) return 'conic-gradient(#e7ecf4 0% 100%)';
    let start = 0;
    return `conic-gradient(${data.relationships.map((item,i) => {
      const end = start + item.count / total * 100;
      const piece = `${relationshipColors[i % relationshipColors.length]} ${start.toFixed(3)}% ${end.toFixed(3)}%`;
      start = end; return piece;
    }).join(',')})`;
  }, [data, total]);
  const stats: { title: string; value?: number; icon: IconName; tone: string; sub: string; target: PageId }[] = [
    { title: 'Thành viên', value: data?.stats.employees, icon: 'users', tone: 'blue', sub: 'Trong tổ chức', target: 'employees' },
    { title: 'Kết nối', value: data?.stats.edges_total, icon: 'network', tone: 'violet', sub: 'Quan hệ nội bộ', target: 'graph' },
    { title: 'Phòng ban', value: data?.stats.departments, icon: 'building', tone: 'teal', sub: 'Nhóm làm việc', target: 'departments' },
    { title: 'Dự án', value: data?.stats.projects, icon: 'briefcase', tone: 'orange', sub: 'Đang theo dõi', target: 'projects' },
  ];
  const maxDept = Math.max(1, ...(data?.departments.map(d => d.employee_count) ?? []));

  return <div className="social-dash">
    <div className="social-welcome-line">
      <div><div className="social-mini-overline"><span className="social-online-pulse"/> LINKO COMMUNITY <span className="social-overline-separator">/</span> WORKSPACE</div><h2>Không gian kết nối của bạn <span aria-hidden="true">✦</span></h2><p>Đội ngũ, công việc và những kết nối quan trọng — tất cả trong một nơi.</p></div>
      <button className="social-refresh" type="button" onClick={() => void load(true)} disabled={reloading}><Icon name="refresh" size={16} className={reloading ? 'rotate-icon' : ''}/>{reloading ? 'Đang làm mới' : 'Làm mới dữ liệu'}</button>
    </div>
    {error && <div className="alert alert-err social-fetch-error" role="alert">{error} <button type="button" className="btn btn-sm btn-ghost" onClick={() => void load(true)}>Thử lại</button></div>}

    <div className="social-metrics">
      {stats.map((s) => <button type="button" className={`social-metric social-metric-${s.tone}`} key={s.title} onClick={() => onNavigate(s.target)}>
        <span className="social-metric-icon"><Icon name={s.icon} size={21}/></span>
        <span className="social-metric-arrow"><Icon name="arrow" size={15}/></span>
        <strong>{loading ? '···' : fmt(s.value)}</strong>
        <span className="social-metric-title">{s.title}</span>
        <small>{s.sub}</small>
      </button>)}
    </div>

    <div className="social-layout">
      <div className="social-column-main">
        <section className="social-hero">
          <div className="social-hero-content">
            <span className="social-hero-chip"><Icon name="sparkles" size={14}/> CÙNG NHAU PHÁT TRIỂN</span>
            <h3>Mọi kết nối đều<br/><em>mở ra cơ hội mới.</em></h3>
            <p>Khám phá đồng nghiệp, tìm đúng người và cùng nhau tạo nên những điều tuyệt vời.</p>
            <div className="social-hero-actions">
              <button type="button" className="social-hero-mainbtn" onClick={() => onNavigate('graph')}><Icon name="network" size={18}/> Khám phá mạng lưới <Icon name="arrow" size={16}/></button>
              <button type="button" className="social-hero-altbtn" onClick={() => onNavigate('feed')}><Icon name="book" size={15}/> Đến bảng tin <Icon name="chevron" size={15}/></button>
            </div>
          </div>
          <div className="social-hero-visual"><ConnectionsIllustration/></div>
          <div className="social-hero-orb social-hero-orb-one"/><div className="social-hero-orb social-hero-orb-two"/>
        </section>

        <section className="social-card social-feed-card">
          <header className="social-card-head"><div><span className="social-eyebrow"><span className="social-eyebrow-dot"/> WORKSPACE FEED</span><h3>Bảng tin dự án</h3><p>Các dự án đang được theo dõi trong tổ chức</p></div><button type="button" className="social-head-link" onClick={() => onNavigate('feed')}>Đến bảng tin <Icon name="arrow" size={16}/></button></header>
          <div className="social-project-feed">
            {data?.projects.length ? data.projects.slice(0,3).map((project,i) => <article className="social-feed-post" key={project.project_id}>
              <div className={`social-feed-logo social-feed-logo-${i % 3}`}><Icon name={i % 2 ? 'layers' : 'briefcase'} size={20}/></div>
              <div className="social-feed-body"><div className="social-feed-top"><div><h4>{project.name}</h4><span><Icon name="building" size={12}/> {project.department}</span></div><span className={`social-feed-state ${project.status === 'ACTIVE' ? 'is-active' : ''}`}><i/>{project.status === 'ACTIVE' ? 'Đang triển khai' : project.status}</span></div><p>Dự án trong mạng lưới cộng tác của tổ chức.</p><button type="button" className="social-feed-action" onClick={() => onNavigate('projects')}>Xem dự án <Icon name="arrow" size={14}/></button></div>
            </article>) : <div className="social-empty">{loading ? 'Đang tải hoạt động dự án…' : 'Chưa có dự án nào để hiển thị.'}</div>}
          </div>
        </section>

        <section className="social-card social-depts">
          <header className="social-card-head"><div><span className="social-eyebrow">OUR TEAMS</span><h3>Phòng ban & thành viên</h3><p>Khám phá cấu trúc đội ngũ của bạn</p></div><button type="button" className="social-head-link" onClick={() => onNavigate('departments')}>Chi tiết <Icon name="arrow" size={16}/></button></header>
          <div className="social-dept-list">{data?.departments.length ? data.departments.slice(0,5).map((dept,i) => <div className="social-dept" key={dept.department_id}><div className="social-dept-head"><span className="social-dept-dot" style={{ background: colors[i % colors.length] }}/><span className="social-dept-name" title={dept.name}>{dept.name}</span><strong>{fmt(dept.employee_count)} <small>người</small></strong></div><div className="social-dept-track"><span style={{width:`${dept.employee_count / maxDept * 100}%`, background: colors[i % colors.length]}}/></div></div>) : <div className="social-empty">{loading ? 'Đang tải danh sách phòng ban…' : 'Chưa có dữ liệu phòng ban.'}</div>}</div>
        </section>
      </div>

      <aside className="social-column-side" aria-label="Thông tin mạng lưới">
        <section className="social-card social-relations">
          <header className="social-card-head"><div><span className="social-eyebrow">NETWORK ANALYTICS</span><h3>Loại kết nối</h3><p>Phân bổ mối quan hệ</p></div><span className="social-analysis-icon"><Icon name="chart" size={18}/></span></header>
          <div className="social-donut-holder"><div className="social-donut" style={{background:donut}} role="img" aria-label={`${fmt(total)} tổng kết nối, chia thành ${data?.relationships.length ?? 0} loại`}><div className="social-donut-inner"><span>TỔNG CỘNG</span><strong>{loading ? '—' : fmt(total)}</strong><small>kết nối</small></div></div></div>
          <div className="social-legend">{data?.relationships.map((item,i) => <div key={item.key} className="social-legend-row"><span className="social-legend-mark" style={{ background: relationshipColors[i % relationshipColors.length]}}/><span className="social-legend-name">{item.name}</span><strong>{fmt(item.count)}</strong><span className="social-legend-percent">{total ? (item.count / total * 100).toFixed(0) : 0}%</span></div>)}{!data && <div className="social-empty">{loading ? 'Đang tải biểu đồ…' : 'Không có dữ liệu.'}</div>}</div>
          <button type="button" className="social-card-bottom-link" onClick={() => onNavigate('insights')}>Xem phân tích chuyên sâu <Icon name="arrow" size={16}/></button>
        </section>

        <section className="social-card social-contacts">
          <header className="social-card-head"><div><span className="social-eyebrow">PEOPLE YOU KNOW</span><h3>Kết nối nổi bật</h3><p>Những người có nhiều kết nối</p></div><span className="social-contacts-count">Top 5</span></header>
          <div className="social-contact-list">{data?.top_people.length ? data.top_people.slice(0,5).map((person,i) => <button key={person.employee_id} type="button" className="social-contact" onClick={() => onSelectEmp ? onSelectEmp(person.employee_id) : onNavigate('employees')}><span className={`social-contact-av social-avatar-${i%5}`}>{initials(person.name)}</span><span className="social-contact-desc"><strong>{person.name}</strong><small>{person.title || person.department}</small></span><span className="social-contact-count"><Icon name="link" size={13}/>{fmt(person.connections)}</span></button>) : <div className="social-empty">{loading ? 'Đang tải danh sách…' : 'Chưa có dữ liệu kết nối.'}</div>}</div>
          <button type="button" className="social-card-bottom-link" onClick={() => onNavigate('employees')}>Khám phá mọi người <Icon name="arrow" size={16}/></button>
        </section>

        <section className="social-side-tip"><span className="social-tip-symbol"><Icon name="route" size={22}/></span><h4>Bạn đã biết đường đi ngắn nhất?</h4><p>Tìm cách kết nối giữa bất kỳ hai thành viên trong tổ chức.</p><button type="button" onClick={() => onNavigate('path')}>Thử ngay <Icon name="arrow" size={15}/></button></section>
      </aside>
    </div>
  </div>;
}

export const DashboardPage = memo(DashboardPageInner);

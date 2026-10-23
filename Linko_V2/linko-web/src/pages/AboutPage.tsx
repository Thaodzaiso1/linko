import { memo } from 'react';
function AboutPageInner() {
  return (
    <>
      <div className="page-eyebrow">Academic · HUFLIT</div>
      <h2 className="page-title">Topic 17 · Internal graph network</h2>
      <p className="page-lede">SQL Property Graph on Oracle Database 23ai. FastAPI + React console.</p>
      <div className="hero-banner">
        <h2>Đề tài 17 — Mạng xã hội nội bộ doanh nghiệp</h2>
        <p>
          Graph Queries &amp; SQL Property Graph trên Oracle Database 23ai. Ứng dụng web Linko gọi
          FastAPI → PL/SQL package / GRAPH_TABLE.
        </p>
      </div>
      <div className="grid-4" style={{ marginBottom: 16 }}>
        <div className="stat"><div className="value">17</div><div className="label">Đề tài</div></div>
        <div className="stat"><div className="value">13</div><div className="label">Nhóm</div></div>
        <div className="stat"><div className="value">3</div><div className="label">Loại cạnh</div></div>
        <div className="stat"><div className="value">11</div><div className="label">Màn hình web</div></div>
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-title">Thành viên</div>
          <ul className="list">
            <li><span>Trần Phi Thao</span><span style={{ color: 'var(--muted)' }}>24DH113379</span></li>
            <li><span>Nguyễn Hoàng Vinh</span><span style={{ color: 'var(--muted)' }}>24DH112995</span></li>
            <li><span>Nguyễn Nhật Tân</span><span style={{ color: 'var(--muted)' }}>24DH113484</span></li>
          </ul>
          <p className="card-desc" style={{ marginTop: 12 }}>
            GVHD: Lê Hồng Thúy Vũ · HUFLIT — Hệ Quản trị Cơ sở dữ liệu 2026
          </p>
        </div>
        <div className="card">
          <div className="card-title">Stack</div>
          <ul className="list">
            <li><span>Oracle Database 23ai Free (Docker)</span><span className="tag tag-wo">DB</span></li>
            <li><span>SQL Property Graph + PL/SQL</span><span className="tag tag-wo">Graph</span></li>
            <li><span>FastAPI + oracledb</span><span className="tag tag-kn">API</span></li>
            <li><span>React 19 + Vite + vis-network</span><span className="tag tag-kn">Web</span></li>
          </ul>
        </div>
      </div>
      <div className="card">
        <div className="card-title">Phím tắt</div>
        <ul className="list">
          <li><span>Tìm nhân viên toàn cục</span><span><kbd>Ctrl</kbd> + <kbd>K</kbd></span></li>
          <li><span>Dark mode</span><span>Nút ☾ / ☀ trên topbar</span></li>
        </ul>
      </div>
    </>
  );
}

export const AboutPage = memo(AboutPageInner);

import { memo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';
import { ROLE_LABEL, type Role } from '../auth/types';

const DEMO: { user: string; pass: string; role: Role }[] = [
  { user: 'admin', pass: 'admin123', role: 'admin' },
  { user: 'manager', pass: 'manager123', role: 'manager' },
  { user: 'viewer', pass: 'viewer123', role: 'viewer' },
];

const LoginArt = memo(function LoginArt() {
  const nodes = [
    [130,150,18],[245,68,14],[279,211,22],[380,122,30],[490,64,17],[526,238,20],[442,324,14],[170,307,12],[336,379,15]
  ];
  const edges = [[0,1],[0,2],[0,7],[1,2],[1,3],[1,4],[2,3],[2,7],[2,8],[3,4],[3,5],[3,6],[4,5],[5,6],[6,8],[7,8]];
  return <svg viewBox="0 0 650 440" fill="none" className="login-visual-network" aria-hidden="true">
    <defs><radialGradient id="login-glow"><stop stopColor="#9280ff" stopOpacity=".28"/><stop offset="1" stopColor="#9280ff" stopOpacity="0"/></radialGradient></defs>
    <circle cx="330" cy="213" r="230" fill="url(#login-glow)"/>
    {edges.map(([a,b],i)=><path key={i} d={`M${nodes[a][0]} ${nodes[a][1]} L${nodes[b][0]} ${nodes[b][1]}`} stroke="#b5a8ff" strokeOpacity={i%3===0?.55:.3} strokeWidth="1.5" strokeDasharray={i%3===0?'5 7':undefined}/>)}
    {nodes.map(([x,y,r],i)=><g key={i}><circle cx={x} cy={y} r={r+11} fill="#cec4ff" fillOpacity=".08"/><circle cx={x} cy={y} r={r} fill="#54459e" stroke="#bfb4ff" strokeWidth="2"/><circle cx={x} cy={y} r={Math.max(r-8,4)} fill={i%4===0?'#7ee0c8':'#cbc2ff'}/></g>)}
    <g transform="translate(295 148)"><rect width="142" height="46" rx="12" fill="#fff"/><circle cx="24" cy="23" r="11" fill="#bfb4ff"/><path d="m20 23 3 3 6-7" stroke="#4d3e96" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><text x="44" y="20" fill="#28234d" fontSize="11" fontWeight="700">Connected</text><text x="44" y="34" fill="#88849d" fontSize="9">Your team is in sync</text></g>
    <g transform="translate(95 244)"><rect width="156" height="50" rx="13" fill="#fff" fillOpacity=".17" stroke="#fff" strokeOpacity=".35"/><circle cx="25" cy="25" r="12" fill="#86e5d2"/><text x="46" y="22" fill="#fff" fontSize="11" fontWeight="700">Team workspace</text><text x="46" y="35" fill="#e5e0ff" fontSize="10">Always connected</text></g>
  </svg>;
});

function LoginPageInner() {
  const { login } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [visible, setVisible] = useState(false);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault(); setErr('');
    if (!username.trim() || !password) { setErr('Vui lòng nhập tài khoản và mật khẩu'); return; }
    setLoading(true);
    try { await login(username.trim(), password); }
    catch (ex) { setErr(ex instanceof Error ? ex.message : 'Đăng nhập thất bại'); }
    finally { setLoading(false); }
  };

  return <div className="login-screen-v2">
    <section className="login-form-side">
      <div className="login-brand-v2"><span className="brand-symbol"><Icon name="network" size={23} strokeWidth={2.2}/></span><span>linko<span className="brand-dot">.</span></span></div>
      <div className="login-form-wrap">
        <span className="login-eyebrow"><span/> WELCOME BACK</span>
        <h1>Chào mừng<br/>trở lại <span>Linko</span></h1>
        <p className="login-intro">Đăng nhập để kết nối với đội ngũ, khám phá mạng lưới quan hệ và quản lý mọi hoạt động trong không gian làm việc của bạn.</p>
        <form onSubmit={submit}>
          <div className="login-field"><label htmlFor="login-username">Tên đăng nhập</label><div className="login-input-wrap"><Icon name="users" size={19}/><input id="login-username" autoComplete="username" placeholder="Nhập tên đăng nhập" value={username} onChange={e=>setUsername(e.target.value)} autoFocus/></div></div>
          <div className="login-field"><label htmlFor="login-password">Mật khẩu</label><div className="login-input-wrap"><Icon name="shield" size={19}/><input id="login-password" type={visible?'text':'password'} autoComplete="current-password" placeholder="Nhập mật khẩu" value={password} onChange={e=>setPassword(e.target.value)}/><button type="button" className="password-eye" aria-label={visible?'Ẩn mật khẩu':'Hiện mật khẩu'} onClick={()=>setVisible(!visible)}><Icon name={visible?'eyeoff':'eye'} size={18}/></button></div></div>
          {err && <div className="alert alert-err" role="alert">{err}</div>}
          <button type="submit" className="login-submit" disabled={loading}>{loading?'Đang xác thực…':'Đăng nhập vào Workspace'}<Icon name="arrow" size={18}/></button>
        </form>
        <div className="login-demo"><div className="login-demo-head"><Icon name="bolt" size={16}/><strong>Trải nghiệm nhanh với tài khoản demo</strong></div><p>Chọn một vai trò để tự động điền thông tin.</p><div className="demo-options">{DEMO.map(d=><button type="button" className={`demo-option${username===d.user?' is-selected':''}`} key={d.user} onClick={()=>{setUsername(d.user);setPassword(d.pass);setErr('')}}><Icon name={d.role==='admin'?'shield':d.role==='manager'?'briefcase':'eye'} size={16}/><span>{ROLE_LABEL[d.role]}</span></button>)}</div><div className="demo-note">Chỉ dành cho môi trường học tập và demo.</div></div>
      </div>
      <div className="login-form-footer">© 2026 Linko Workspace <span>Privacy &amp; Security</span></div>
    </section>
    <aside className="login-visual-side">
      <div className="login-visual-top"><span className="login-small-pill"><span/> NEXT GEN WORKSPACE</span><span>01 — 03</span></div>
      <LoginArt/>
      <div className="login-visual-copy"><div className="login-quote-mark">“</div><h2>Mọi kết nối đều<br/>tạo nên giá trị.</h2><p>Xây dựng tổ chức thông minh hơn — nơi con người, dự án và mối quan hệ được kết nối trong một không gian duy nhất.</p><div className="login-visual-chips"><span><Icon name="check" size={15}/> Đồng bộ tổ chức</span><span><Icon name="check" size={15}/> Mạng lưới trực quan</span><span><Icon name="check" size={15}/> Phân tích quan hệ</span></div></div>
      <div className="login-visual-foot"><span>LINKO NETWORK INTELLIGENCE</span><div><span className="active"/><span/><span/></div></div>
    </aside>
  </div>;
}

export const LoginPage = memo(LoginPageInner);

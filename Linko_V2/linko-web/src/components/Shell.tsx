import { memo, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { PageId } from '../app/App';
import { GlobalSearch } from './GlobalSearch';
import { ShortcutsHelp } from './ShortcutsHelp';
import { Icon, type IconName } from './Icon';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type NavItem = { id: PageId; label: string; icon: IconName; group: string };

const NAV: NavItem[] = [
  { id: 'dashboard', label: 'Tổng quan', icon: 'dashboard', group: 'Không gian làm việc' },
  { id: 'feed', label: 'Bảng tin', icon: 'book', group: 'Không gian làm việc' },
  { id: 'messages', label: 'Tin nhắn', icon: 'mail', group: 'Không gian làm việc' },
  { id: 'employees', label: 'Nhân viên', icon: 'users', group: 'Không gian làm việc' },
  { id: 'departments', label: 'Phòng ban', icon: 'building', group: 'Không gian làm việc' },
  { id: 'projects', label: 'Dự án', icon: 'briefcase', group: 'Không gian làm việc' },
  { id: 'graph', label: 'Mạng lưới', icon: 'network', group: 'Khám phá kết nối' },
  { id: 'path', label: 'Đường đi ngắn nhất', icon: 'route', group: 'Khám phá kết nối' },
  { id: 'common', label: 'Kết nối chung', icon: 'link', group: 'Khám phá kết nối' },
  { id: 'org', label: 'Sơ đồ tổ chức', icon: 'layers', group: 'Khám phá kết nối' },
  { id: 'insights', label: 'Phân tích', icon: 'chart', group: 'Quản trị hệ thống' },
  { id: 'audit', label: 'Nhật ký hoạt động', icon: 'activity', group: 'Quản trị hệ thống' },
  { id: 'data', label: 'Sao lưu dữ liệu', icon: 'database', group: 'Quản trị hệ thống' },
  { id: 'about', label: 'Về Linko', icon: 'help', group: 'Quản trị hệ thống' },
  { id: 'detail', label: 'Thông tin nhân viên', icon: 'users', group: 'Không gian làm việc' },
];

const DESC: Partial<Record<PageId, string>> = {
  dashboard: 'Theo dõi mọi thứ đang diễn ra trong tổ chức',
  feed: 'Bài viết, thảo luận và thông báo từ đồng nghiệp',
  messages: 'Nhắn tin riêng với thành viên của Linko',
  employees: 'Danh bạ và quản lý nhân sự',
  departments: 'Các bộ phận và thành viên trong tổ chức',
  projects: 'Dự án và đội ngũ cộng tác',
  graph: 'Khám phá bản đồ quan hệ nội bộ',
  path: 'Tìm kết nối gần nhất giữa hai nhân viên',
  insights: 'Các chỉ số quan trọng về mạng lưới',
};

type Props = {
  page: PageId;
  onNavigate: (p: PageId) => void;
  mode: 'mock' | 'oracle' | 'offline';
  onSelectEmp: (id: number) => void;
  onSearchEmployees: (q: string) => void;
  children: ReactNode;
};

function ShellInner({ page, onNavigate, mode, onSelectEmp, onSearchEmployees, children }: Props) {
  const { user, logout, roleLabel } = useAuth();
  const [helpOpen, setHelpOpen] = useState(false);
  const [feedUnread, setFeedUnread] = useState(0);
  const [chatUnread, setChatUnread] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [metrics, setMetrics] = useState<{ employees?: number; edges?: number } | null>(null);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));

  // Refresh both unread badges on navigation and periodically while tab is visible.
  useEffect(() => {
    let alive = true;
    const refresh = async () => {
      if (document.visibilityState === 'hidden') return;
      try {
        const counts = await api.socialUnread();
        if (alive) {
          setFeedUnread(counts.notifications);
          setChatUnread(counts.messages);
        }
      } catch { /* transient network issue: keep last known unread counts */ }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    window.addEventListener('focus', refresh);
    return () => {
      alive = false;
      window.clearInterval(timer);
      window.removeEventListener('focus', refresh);
    };
  }, [page, user?.username]);

  // Chỉ fetch metrics khi mode đổi — không refetch mỗi lần đổi trang
  useEffect(() => {
    let cancelled = false;
    api
      .metrics()
      .then((m) => {
        if (!cancelled) setMetrics(m);
      })
      .catch(() => {
        if (!cancelled) setMetrics(null);
      });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === '?' &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target instanceof HTMLSelectElement)
      ) {
        e.preventDefault();
        setHelpOpen(true);
      }
      if (e.key === 'Escape') {
        setHelpOpen(false);
        setMobileOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    try {
      localStorage.setItem('linko-theme', dark ? 'dark' : 'light');
    } catch {
      /* blocked */
    }
  }, [dark]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  const visibleNav = useMemo(
    () =>
      NAV.filter(
        (item) =>
          item.id !== 'detail' &&
          !(user?.role === 'viewer' && (item.id === 'data' || item.id === 'audit'))
      ),
    [user?.role]
  );

  const current = useMemo(
    () => NAV.find((item) => item.id === page) || NAV[0],
    [page]
  );

  const navigate = useCallback(
    (id: PageId) => {
      onNavigate(id);
      setMobileOpen(false);
    },
    [onNavigate]
  );

  const toggleDark = useCallback(() => setDark((v) => !v), []);
  const openHelp = useCallback(() => {
    setHelpOpen(true);
    setMobileOpen(false);
  }, []);
  const closeHelp = useCallback(() => setHelpOpen(false), []);
  const openMobile = useCallback(() => setMobileOpen(true), []);
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const displayName = user?.full_name || user?.username || 'Thành viên';
  const initials = useMemo(
    () =>
      displayName
        .trim()
        .split(/\s+/)
        .slice(-2)
        .map((word) => word[0])
        .join('')
        .toUpperCase(),
    [displayName]
  );
  const online = mode !== 'offline';

  // Build nav sections once per visibleNav change
  const navSections = useMemo(() => {
    const sections: { group: string; items: NavItem[] }[] = [];
    let currentGroup = '';
    for (const item of visibleNav) {
      if (item.group !== currentGroup) {
        currentGroup = item.group;
        sections.push({ group: item.group, items: [] });
      }
      sections[sections.length - 1].items.push(item);
    }
    return sections;
  }, [visibleNav]);

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          type="button"
          className="mobile-overlay"
          aria-label="Đóng menu"
          onClick={closeMobile}
        />
      )}
      <aside className={`sidebar${mobileOpen ? ' sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-symbol">
            <Icon name="network" size={22} strokeWidth={2.2} />
          </div>
          <div className="brand-copy">
            <div className="name">
              linko<span className="brand-dot">.</span>
            </div>
            <div className="sub">SOCIAL WORKSPACE</div>
          </div>
          <button
            type="button"
            className="mobile-close"
            aria-label="Đóng menu"
            onClick={closeMobile}
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="workspace-picker">
          <div className="workspace-icon">L</div>
          <div className="workspace-meta">
            <strong>Linko Workspace</strong>
            <span>Cùng kết nối và phát triển</span>
          </div>
          <Icon name="chevron" size={15} className="workspace-arrow" />
        </div>

        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          {navSections.map((section) => (
            <div key={section.group}>
              <div className="nav-section">{section.group}</div>
              {section.items.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className={`nav-item${page === item.id ? ' active' : ''}`}
                  onClick={() => navigate(item.id)}
                  aria-current={page === item.id ? 'page' : undefined}
                >
                  <Icon name={item.icon} size={18} />
                  <span>{item.label}</span>
                  {item.id === 'messages' && chatUnread > 0 && <span className="linko-nav-unread" aria-label={`${chatUnread} tin nhắn chưa đọc`}>{chatUnread > 99 ? '99+' : chatUnread}</span>}
                  {item.id === 'feed' && feedUnread > 0 && <span className="linko-nav-unread" aria-label={`${feedUnread} thông báo chưa đọc`}>{feedUnread > 99 ? '99+' : feedUnread}</span>}
                  {page === item.id && <span className="nav-active-dot" />}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-helpbox">
            <div className="helpbox-icon">
              <Icon name="sparkles" size={18} />
            </div>
            <strong>Khám phá nhanh hơn</strong>
            <p>
              Nhấn <kbd>Ctrl</kbd> + <kbd>K</kbd> để tìm kiếm nhân viên.
            </p>
            <button type="button" onClick={openHelp}>
              Xem phím tắt <Icon name="arrow" size={14} />
            </button>
          </div>
          <div className="sidebar-account">
            <div className="profile-avatar">{initials}</div>
            <div className="profile-meta">
              <strong title={displayName}>{displayName}</strong>
              <span>{roleLabel}</span>
            </div>
            <button
              type="button"
              className="logout-button"
              onClick={logout}
              title="Đăng xuất"
              aria-label="Đăng xuất"
            >
              <Icon name="logout" size={18} />
            </button>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu"
              aria-label="Mở menu"
              onClick={openMobile}
            >
              <Icon name="menu" size={22} />
            </button>
            <div className="breadcrumb">
              <span>Linko Workspace</span>
              <Icon name="chevron" size={14} />
              <strong>{current.label}</strong>
            </div>
          </div>
          <div className="topbar-right">
            <GlobalSearch onSelectEmp={onSelectEmp} onSearchAll={onSearchEmployees} />
            <div className="social-header-quick" aria-label="Truy cập nhanh">
              <button type="button" className={page === 'dashboard' ? 'on' : ''} title="Trang chủ" aria-label="Trang chủ" onClick={() => navigate('dashboard')}><Icon name="dashboard" size={19}/></button>
              <button type="button" className={page === 'feed' ? 'on' : ''} title="Bảng tin" aria-label="Bảng tin" onClick={() => navigate('feed')}><Icon name="book" size={19}/></button>
              <button type="button" className={page === 'messages' ? 'on' : ''} title="Tin nhắn" aria-label="Tin nhắn" onClick={() => navigate('messages')}><Icon name="mail" size={19}/></button>
              <button type="button" className={page === 'employees' ? 'on' : ''} title="Danh bạ" aria-label="Danh bạ" onClick={() => navigate('employees')}><Icon name="users" size={19}/></button>
              <button type="button" className={page === 'graph' ? 'on' : ''} title="Mạng lưới" aria-label="Mạng lưới" onClick={() => navigate('graph')}><Icon name="network" size={19}/></button>
            </div>
            <span className={`live-indicator ${online ? '' : 'is-offline'}`}>
              <i />
              {mode === 'oracle'
                ? 'Oracle Live'
                : mode === 'mock'
                  ? 'Dữ liệu demo'
                  : 'Mất kết nối'}
            </span>
            <button
              type="button"
              className="topbar-icon-btn"
              aria-label={dark ? 'Chế độ sáng' : 'Chế độ tối'}
              title="Đổi giao diện"
              onClick={toggleDark}
            >
              <Icon name={dark ? 'sun' : 'moon'} size={19} />
            </button>
            <div className="topbar-avatar" title={displayName}>
              {initials}
            </div>
          </div>
        </header>
        <main className="content">
          <div className="content-heading">
            <div>
              <div className="content-overline">
                <span className="content-overline-dot" /> YOUR WORKSPACE
              </div>
              <h1>{current.label}</h1>
              <p>
                {DESC[page] ||
                  'Kết nối dữ liệu, con người và công việc tại một nơi.'}
              </p>
            </div>
            <div className="content-heading-meta">
              <Icon name="activity" size={15} />
              <span>{metrics?.employees ?? '—'} thành viên đang kết nối</span>
            </div>
          </div>
          {children}
          <footer className="app-footer">
            <span>© 2026 Linko Workspace · Connect. Collaborate. Grow.</span>
            <span>Đề tài 17 · Nhóm 13 · API v5 · Premium</span>
          </footer>
        </main>
      </div>
      <ShortcutsHelp open={helpOpen} onClose={closeHelp} />
    </div>
  );
}

export const Shell = memo(ShellInner);

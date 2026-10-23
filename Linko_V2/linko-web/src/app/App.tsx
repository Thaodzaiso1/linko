import { lazy, Suspense, useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { Shell } from '../components/Shell';
import { ToastHost } from '../components/Toast';
import { useAuth } from '../auth/AuthContext';
import { LoginPage } from '../pages/LoginPage';

export type PageId =
  | 'dashboard'
  | 'feed'
  | 'messages'
  | 'path'
  | 'employees'
  | 'detail'
  | 'departments'
  | 'projects'
  | 'common'
  | 'org'
  | 'audit'
  | 'graph'
  | 'insights'
  | 'data'
  | 'about';

const MessagesPage = lazy(() =>
  import('../pages/MessagesPage').then((m) => ({ default: m.MessagesPage }))
);
const FeedPage = lazy(() =>
  import('../pages/FeedPage').then((m) => ({ default: m.FeedPage }))
);
const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const PathPage = lazy(() =>
  import('../pages/PathPage').then((m) => ({ default: m.PathPage }))
);
const EmployeesPage = lazy(() =>
  import('../pages/EmployeesPage').then((m) => ({ default: m.EmployeesPage }))
);
const DetailPage = lazy(() =>
  import('../pages/DetailPage').then((m) => ({ default: m.DetailPage }))
);
const DepartmentsPage = lazy(() =>
  import('../pages/DepartmentsPage').then((m) => ({ default: m.DepartmentsPage }))
);
const ProjectsPage = lazy(() =>
  import('../pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage }))
);
const CommonPage = lazy(() =>
  import('../pages/CommonPage').then((m) => ({ default: m.CommonPage }))
);
const OrgPage = lazy(() =>
  import('../pages/OrgPage').then((m) => ({ default: m.OrgPage }))
);
const AuditPage = lazy(() =>
  import('../pages/AuditPage').then((m) => ({ default: m.AuditPage }))
);
const GraphPage = lazy(() =>
  import('../pages/GraphPage').then((m) => ({ default: m.GraphPage }))
);
const InsightsPage = lazy(() =>
  import('../pages/InsightsPage').then((m) => ({ default: m.InsightsPage }))
);
const DataPage = lazy(() =>
  import('../pages/DataPage').then((m) => ({ default: m.DataPage }))
);
const AboutPage = lazy(() =>
  import('../pages/AboutPage').then((m) => ({ default: m.AboutPage }))
);

function pageFromHash(): PageId {
  const h = (window.location.hash || '#dashboard').replace('#', '') as PageId;
  const allowed: PageId[] = [
    'dashboard', 'feed', 'messages', 'path', 'employees', 'detail', 'departments', 'projects',
    'common', 'org', 'audit', 'graph', 'insights', 'data', 'about',
  ];
  return allowed.includes(h) ? h : 'dashboard';
}

function PageFallback() {
  return (
    <div className="page-fallback" role="status" aria-live="polite">
      <span className="page-fallback-spinner" />
      <span>Đang tải trang…</span>
    </div>
  );
}

export default function App() {
  const { user } = useAuth();
  const [page, setPage] = useState<PageId>(pageFromHash);
  const [mode, setMode] = useState<'mock' | 'oracle' | 'offline'>('mock');
  const [selectedEmp, setSelectedEmp] = useState<number>(20);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((h) => {
        if (!cancelled) setMode(h.mode === 'oracle' ? 'oracle' : 'mock');
      })
      .catch(() => {
        if (!cancelled) setMode('offline');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const el = document.querySelector('.global-search input') as HTMLInputElement | null;
        el?.focus();
        el?.select();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const navigate = useCallback((p: PageId) => {
    window.location.hash = p;
    setPage(p);
  }, []);

  const goDetail = useCallback(
    (id: number) => {
      setSelectedEmp(id);
      navigate('detail');
    },
    [navigate]
  );

  const onSearchEmployees = useCallback(
    (q: string) => {
      setSearchQuery(q);
      navigate('employees');
    },
    [navigate]
  );

  if (!user) {
    return (
      <>
        <LoginPage />
        <ToastHost />
      </>
    );
  }

  return (
    <>
      <Shell
        page={page}
        onNavigate={navigate}
        mode={mode}
        onSelectEmp={goDetail}
        onSearchEmployees={onSearchEmployees}
      >
        <Suspense fallback={<PageFallback />}>
          {page === 'dashboard' && <DashboardPage onNavigate={navigate} onSelectEmp={goDetail} />}
          {page === 'feed' && <FeedPage />}
          {page === 'messages' && <MessagesPage />}
          {page === 'path' && <PathPage onSelectEmp={goDetail} />}
          {page === 'employees' && (
            <EmployeesPage onSelect={goDetail} initialQuery={searchQuery} />
          )}
          {page === 'detail' && (
            <DetailPage employeeId={selectedEmp} onChangeEmp={setSelectedEmp} />
          )}
          {page === 'departments' && <DepartmentsPage onSelectEmp={goDetail} />}
          {page === 'projects' && <ProjectsPage onSelectEmp={goDetail} />}
          {page === 'common' && <CommonPage onSelectEmp={goDetail} />}
          {page === 'org' && <OrgPage onSelectEmp={goDetail} />}
          {page === 'audit' && <AuditPage />}
          {page === 'graph' && <GraphPage />}
          {page === 'insights' && <InsightsPage onSelectEmp={goDetail} />}
          {page === 'data' && <DataPage />}
          {page === 'about' && <AboutPage />}
        </Suspense>
      </Shell>
      <ToastHost />
    </>
  );
}

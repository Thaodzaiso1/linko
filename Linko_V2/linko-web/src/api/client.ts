const BASE = import.meta.env.VITE_API_BASE_URL || '';

/** Lightweight in-memory GET cache (TTL ms). Avoids refetch storms on nav. */
const GET_CACHE = new Map<string, { at: number; data: unknown }>();
const DEFAULT_TTL = 15_000;

function cacheKey(path: string, init?: RequestInit): string | null {
  if (init?.method && init.method.toUpperCase() !== 'GET') return null;
  // Keep cached data isolated per login session to prevent cross-account disclosure.
  return `${authHeaders().Authorization || 'anonymous'}:${path}`;
}

function getCached<T>(key: string, ttl = DEFAULT_TTL): T | undefined {
  const hit = GET_CACHE.get(key);
  if (!hit) return undefined;
  if (Date.now() - hit.at > ttl) {
    GET_CACHE.delete(key);
    return undefined;
  }
  return hit.data as T;
}

function setCache(key: string, data: unknown) {
  GET_CACHE.set(key, { at: Date.now(), data });
}

/** Invalidate cache after mutations (create/update/delete). */
export function invalidateApiCache(prefix?: string) {
  if (!prefix) {
    GET_CACHE.clear();
    return;
  }
  for (const k of [...GET_CACHE.keys()]) {
    if (k.startsWith(prefix)) GET_CACHE.delete(k);
  }
}

function authHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem('linko-auth');
    if (!raw) return {};
    const u = JSON.parse(raw) as { token?: string };
    return u?.token ? { Authorization: `Bearer ${u.token}` } : {};
  } catch {
    return {};
  }
}

async function req<T>(path: string, init?: RequestInit, opts?: { ttl?: number; noCache?: boolean }): Promise<T> {
  const key = opts?.noCache ? null : cacheKey(path, init);
  if (key) {
    const cached = getCached<T>(key, opts?.ttl);
    if (cached !== undefined) return cached;
  }

  // Avoid an indefinitely hanging UI when a dev API server is offline.
  const controller = new AbortController();
  const abortExternal = () => controller.abort();
  init?.signal?.addEventListener('abort', abortExternal, { once: true });
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...(init?.headers || {}),
      },
    });
  } catch (err) {
    if (controller.signal.aborted) throw new Error('Yêu cầu quá thời gian chờ (15 giây) hoặc đã bị hủy.');
    throw new Error('Không kết nối được máy chủ Linko. Hãy chạy CHAY_BACKEND.bat và thử lại.');
  } finally {
    window.clearTimeout(timeout);
    init?.signal?.removeEventListener('abort', abortExternal);
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === 'string' ? j.detail : j.detail?.msg || JSON.stringify(j.detail || j) || msg;
    } catch {
      try {
        msg = await res.text() || msg;
      } catch {
        /* ignore */
      }
    }
    if (res.status === 401 && path !== '/api/auth/login') {
      invalidateApiCache();
      window.dispatchEvent(new Event('linko:auth-expired'));
    }
    if (res.status === 401 || res.status === 403) {
      throw new Error(typeof msg === 'string' ? msg : 'Không có quyền hoặc chưa đăng nhập');
    }
    throw new Error(typeof msg === 'string' ? msg : String(msg));
  }
  const data = (await res.json()) as T;
  if (key) {
    setCache(key, data);
  } else {
    // Mutation: drop caches so lists/dashboard refresh next time
    const method = (init?.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
      GET_CACHE.clear();
    }
  }
  return data;
}

export type Employee = {
  employee_id: number;
  full_name: string;
  email?: string;
  title?: string;
  department_id?: number;
  department_name?: string;
  status?: string;
};

export type PathStep = {
  from_id: number;
  from_name: string;
  from_title?: string;
  to_id: number;
  to_name: string;
  to_title?: string;
  relation: string;
  relation_type: string;
};

export type PathResult = {
  found: boolean;
  message?: string;
  path_length?: number;
  nodes?: Employee[];
  steps?: PathStep[];
  from?: Employee;
  to?: Employee;
};

export type DashboardOverview = {
  generated_at: string;
  stats: { employees: number; departments: number; projects: number; edges_total: number; edges_knows: number; edges_reports_to: number; edges_works_on: number; mode: string };
  departments: { department_id: number; name: string; employee_count: number; project_count: number }[];
  relationships: { key: string; name: string; count: number }[];
  top_people: { employee_id: number; name: string; title: string; department: string; connections: number }[];
  projects: { project_id: number; name: string; status: string; department: string }[];
};

export type FeedPost = {
  id: number;
  author_username: string;
  author_name: string;
  content: string;
  created_at: string;
  updated_at?: string | null;
  likes_count: number;
  comments_count: number;
  liked_by_me: boolean;
  bookmarked_by_me: boolean;
};
export type FeedComment = { id: number; post_id: number; author_username: string; author_name: string; content: string; created_at: string };
export type FeedNotification = { id: number; actor_name: string; actor_username: string; message: string; kind: string; post_id: number; is_read: number; created_at: string };
export type FeedPageData = { items: FeedPost[]; total: number; page: number; page_size: number; pages: number };

export type MessagePeer = { username: string; full_name: string; role: string; last_message: string | null; last_at: string | null; unread: number };
export type DirectMessage = { id: number; sender_username: string; receiver_username: string; content: string; created_at: string; is_read: number };
export const api = {
  messagePeers: () => req<MessagePeer[]>('/api/social/messages/peers', undefined, { noCache: true }),
  searchMessages: (q: string, peer?: string) => req<DirectMessage[]>(`/api/social/messages/search?q=${encodeURIComponent(q)}${peer ? `&peer=${encodeURIComponent(peer)}` : ''}`, undefined, { noCache: true }),
  directMessages: (peer: string, beforeId?: number) => req<DirectMessage[]>(`/api/social/messages/${encodeURIComponent(peer)}?limit=50${beforeId ? `&before_id=${beforeId}` : ''}`, undefined, { noCache: true }),
  sendDirectMessage: (to_username: string, content: string) => req<DirectMessage>('/api/social/messages', { method: 'POST', body: JSON.stringify({ to_username, content }) }),
  markMessagesRead: (peer: string) => req<{ ok: boolean }>(`/api/social/messages/${encodeURIComponent(peer)}/read`, { method: 'POST', body: '{}' }),

  socialPosts: (page = 1, page_size = 10, q = '', view: 'all' | 'mine' | 'saved' = 'all') => req<FeedPageData>(`/api/social/posts?page=${page}&page_size=${page_size}&q=${encodeURIComponent(q)}&view=${view}`, undefined, { noCache: true }),
  socialBookmark: (id: number) => req<{ post_id: number; bookmarked_by_me: boolean }>(`/api/social/posts/${id}/bookmark`, { method: 'POST', body: '{}' }),
  socialCreatePost: (content: string) => req<FeedPost>('/api/social/posts', { method: 'POST', body: JSON.stringify({ content }) }),
  socialDeletePost: (id: number) => req<{ ok: boolean }>(`/api/social/posts/${id}`, { method: 'DELETE' }),
  socialEditPost: (id: number, content: string) => req<FeedPost>(`/api/social/posts/${id}`, { method: 'PUT', body: JSON.stringify({ content }) }),
  socialLike: (id: number) => req<{ liked_by_me: boolean; likes_count: number }>(`/api/social/posts/${id}/like`, { method: 'POST', body: '{}' }),
  socialComments: (id: number) => req<FeedComment[]>(`/api/social/posts/${id}/comments`, undefined, { noCache: true }),
  socialAddComment: (id: number, content: string) => req<FeedComment>(`/api/social/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ content }) }),
  socialDeleteComment: (id: number) => req<{ ok: boolean; post_id: number }>(`/api/social/comments/${id}`, { method: 'DELETE' }),
  socialNotifications: () => req<{ items: FeedNotification[]; unread: number }>('/api/social/notifications', undefined, { noCache: true }),
  socialReadNotifications: () => req<{ ok: boolean; unread: number }>('/api/social/notifications/read', { method: 'POST', body: '{}' }),
  socialReadNotification: (id: number) => req<{ ok: boolean; unread: number }>(`/api/social/notifications/${id}/read`, { method: 'POST', body: '{}' }),
  socialUnread: () => req<{ notifications: number; messages: number; total: number }>('/api/social/unread', undefined, { noCache: true }),
  socialSummary: () => req<{ posts: number; comments: number; likes: number }>('/api/social/summary'),

  dashboardOverview: () => req<DashboardOverview>('/api/dashboard/overview'),
  login: (username: string, password: string) =>
    req<{
      token: string;
      username: string;
      full_name: string;
      role: string;
      expires_in: number;
    }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => req<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  me: () =>
    req<{ username: string; full_name: string; role: string }>('/api/auth/me', undefined, { noCache: true }),
  authPermissions: () =>
    req<{
      roles: Record<string, string[]>;
      matrix: Record<string, string[]>;
      current: { username: string; role: string; perms: string[] } | null;
    }>('/api/auth/permissions'),
  health: () => req<{ status: string; mode: string; framework?: string }>('/api/health'),
  employees: (q?: string) =>
    req<Employee[]>(`/api/employees${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  employee: (id: number) => req<Employee>(`/api/employees/${id}`),
  createEmployee: (body: {
    full_name: string;
    email?: string;
    title?: string;
    department_id?: number;
    department_name?: string;
    status?: string;
  }) =>
    req<Employee>('/api/employees', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateEmployee: (
    id: number,
    body: {
      full_name?: string;
      email?: string;
      title?: string;
      department_id?: number;
      department_name?: string;
      status?: string;
    }
  ) =>
    req<Employee>(`/api/employees/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  deleteEmployee: (id: number) =>
    req<{ ok: boolean }>(`/api/employees/${id}`, { method: 'DELETE' }),
  departments: () => req<unknown[]>('/api/departments'),
  projects: () => req<unknown[]>('/api/projects'),
  shortestPath: (from_id: number, to_id: number, max_hops = 6) =>
    req<PathResult>('/api/paths/shortest', {
      method: 'POST',
      body: JSON.stringify({ from_id, to_id, max_hops }),
    }),
  connections: (id: number) =>
    req<(Employee & { relation?: string; relation_type?: string })[]>(
      `/api/employees/${id}/connections`
    ),
  teammates: (id: number) => req<Employee[]>(`/api/employees/${id}/teammates`),
  managers: (id: number) => req<Employee[]>(`/api/employees/${id}/managers`),
  stats: (id: number) =>
    req<{ outgoing?: number; incoming?: number; projects?: number; summary?: string }>(
      `/api/employees/${id}/stats`
    ),

  commonConnections: (id: number, otherId: number) =>
    req<Employee[]>(`/api/employees/${id}/common/${otherId}`),
  projectMembers: (projectId: number) =>
    req<(Employee & { role?: string; project_hint?: string })[]>(
      `/api/projects/${projectId}/members`
    ),
  createConnection: (body: {
    from_id: number;
    to_id: number;
    connection_type?: string;
    strength?: number;
    notes?: string;
  }) =>
    req<{ ok: boolean; message?: string }>('/api/connections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  dataBackup: () => req<Record<string, unknown>>('/api/data/backup'),
  dataRestore: (body: Record<string, unknown>) =>
    req<{ ok: boolean; message?: string; employees?: number; edges?: number }>(
      '/api/data/restore',
      { method: 'POST', body: JSON.stringify(body) }
    ),
  dataReset: () =>
    req<{ ok: boolean; message?: string }>('/api/data/reset', { method: 'POST', body: '{}' }),
  statsOverview: () =>
    req<{
      employees: number;
      departments: number;
      projects: number;
      edges_total: number;
      edges_knows: number;
      edges_reports_to: number;
      edges_works_on: number;
      mode: string;
    }>('/api/stats/overview'),
  orgTree: (root_id?: number) =>
    req<{ trees: any[]; mode: string }>(
      `/api/org/tree${root_id != null ? `?root_id=${root_id}` : ''}`
    ),
  auditRecent: (limit = 20) =>
    req<
      {
        id: number;
        action: string;
        from_id?: number;
        to_id?: number;
        from_name?: string;
        to_name?: string;
        label?: string;
        at?: string;
      }[]
    >(`/api/audit/recent?limit=${limit}`),
  graphOverview: (limit = 30) =>
    req<{
      nodes: { id: number; label: string; title?: string; group?: number }[];
      edges: { id: number; from: number; to: number; label?: string; arrows?: string; color?: string }[];
    }>(`/api/graph/overview?limit=${limit}`),

  metrics: () =>
    req<{
      version: string;
      mode: string;
      employees: number;
      edges: number;
      edges_by_type: Record<string, number>;
    }>('/api/metrics'),
  searchEmployees: (params: {
    q?: string;
    page?: number;
    page_size?: number;
    department_id?: number;
    sort?: string;
  }) => {
    const sp = new URLSearchParams();
    if (params.q) sp.set('q', params.q);
    if (params.page) sp.set('page', String(params.page));
    if (params.page_size) sp.set('page_size', String(params.page_size));
    if (params.department_id != null) sp.set('department_id', String(params.department_id));
    if (params.sort) sp.set('sort', params.sort);
    return req<{
      items: Employee[];
      total: number;
      page: number;
      page_size: number;
      pages: number;
    }>(`/api/search/employees?${sp}`);
  },
  shortestPathFiltered: (
    from_id: number,
    to_id: number,
    max_hops = 6,
    edge_types?: string[]
  ) =>
    req<PathResult>('/api/paths/shortest/filtered', {
      method: 'POST',
      body: JSON.stringify({ from_id, to_id, max_hops, edge_types }),
    }),
  kShortest: (from_id: number, to_id: number, k = 3) =>
    req<{ found: number; paths: { path_length: number; nodes: Employee[] }[] }>(
      `/api/paths/k-shortest?from_id=${from_id}&to_id=${to_id}&k=${k}`
    ),
  neighborhood: (id: number, depth = 1) =>
    req<{
      center_id: number;
      depth: number;
      node_count: number;
      edge_count: number;
      nodes: Employee[];
      edges: { from: number; to: number; type: string; label: string }[];
    }>(`/api/graph/neighborhood/${id}?depth=${depth}`),
  centrality: (limit = 15) =>
    req<{
      metric: string;
      ranking: (Employee & { degree: number; rank: number })[];
    }>(`/api/graph/centrality?limit=${limit}`),
  components: () =>
    req<{
      component_count: number;
      largest: number;
      components: { size: number; member_ids: number[]; members: string[] }[];
    }>('/api/graph/components'),
  diameter: (sample = 12) =>
    req<{
      estimated_diameter: number;
      pair: { from_id: number; to_id: number; from_name: string; to_name: string } | null;
    }>(`/api/graph/diameter?sample=${sample}`),
  pathExists: (from_id: number, to_id: number) =>
    req<{ exists: boolean; path_length?: number }>(
      `/api/paths/exists?from_id=${from_id}&to_id=${to_id}`
    ),
  exportEmployeesCsvUrl: () => `${BASE}/api/export/employees.csv`,
  exportEdgesCsvUrl: () => `${BASE}/api/export/edges.csv`,
  nodeDegree: (id: number) =>
    req<{
      out_degree: number;
      in_degree: number;
      by_type: Record<string, number>;
      total_touching: number;
    }>(`/api/graph/degree/${id}`),
  subordinates: (id: number, max_depth = 3) =>
    req<{ count: number; subordinates: (Employee & { depth: number })[] }>(
      `/api/employees/${id}/subordinates?max_depth=${max_depth}`
    ),

  // ── Organization ──
  departmentsStats: () =>
    req<
      { department_id: number; department_name: string; location?: string; employee_count: number; project_count: number }[]
    >('/api/departments/stats'),
  department: (id: number) =>
    req<{ department_id: number; department_name: string; location?: string }>(`/api/departments/${id}`),
  departmentEmployees: (id: number) => req<Employee[]>(`/api/departments/${id}/employees`),
  departmentProjects: (id: number) => req<unknown[]>(`/api/departments/${id}/projects`),
  createDepartment: (body: { department_name: string; location?: string }) =>
    req<unknown>('/api/departments', { method: 'POST', body: JSON.stringify(body) }),
  updateDepartment: (id: number, body: { department_name: string; location?: string }) =>
    req<unknown>(`/api/departments/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteDepartment: (id: number) =>
    req<{ deleted: number }>(`/api/departments/${id}`, { method: 'DELETE' }),
  project: (id: number) => req<unknown>(`/api/projects/${id}`),
  createProject: (body: { project_name: string; status?: string; department_id?: number }) =>
    req<unknown>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  updateProject: (id: number, body: { project_name: string; status?: string; department_id?: number }) =>
    req<unknown>(`/api/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteProject: (id: number) =>
    req<{ deleted: number }>(`/api/projects/${id}`, { method: 'DELETE' }),
  orgSummary: () =>
    req<{ departments: number; projects: number; employees: number; active_projects: number }>('/api/org/summary'),
};


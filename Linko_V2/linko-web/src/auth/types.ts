export type Role = 'admin' | 'manager' | 'viewer';

export type AuthUser = {
  username: string;
  full_name: string;
  role: Role;
  token: string;
  expires_at?: number; // Epoch milliseconds (demo session expiry)
};

/** Quyền theo role */
export const PERMS = {
  canView: true as const, // all roles
  canCreateEmployee: (r: Role) => r === 'admin' || r === 'manager',
  canEditEmployee: (r: Role) => r === 'admin' || r === 'manager',
  canDeleteEmployee: (r: Role) => r === 'admin',
  canCreateConnection: (r: Role) => r === 'admin' || r === 'manager',
  canBackup: (r: Role) => r === 'admin' || r === 'manager',
  canRestore: (r: Role) => r === 'admin',
  canReset: (r: Role) => r === 'admin',
  canViewAudit: (r: Role) => r === 'admin' || r === 'manager',
  canViewInsights: (r: Role) => true,
  canRunPath: (r: Role) => true,
};

export const ROLE_LABEL: Record<Role, string> = {
  admin: 'Quản trị',
  manager: 'Quản lý',
  viewer: 'Chỉ xem',
};

import type { Account, AccountInvite, AccountUser, PermissionInfo, RoleInfo } from '@/types/writer'
import api from '../index'

export default {
  me: () => api.get<Account>('/api/accounts/me'),

  list: () => api.get<{ items: Account[], total: number }>('/api/accounts'),

  create: (data: { code: string, name: string }) =>
    api.post<Account>('/api/accounts', data),

  updateStatus: (accountId: number, status: 'active' | 'disabled') =>
    api.put<Account>(`/api/accounts/${accountId}/status`, { status }),

  listUsers: (accountId: number) =>
    api.get<{ account: Account, items: AccountUser[], total: number }>(`/api/accounts/${accountId}/users`),

  updateUserRole: (accountId: number, userId: number, role: string) =>
    api.put<{ id: number, role: string }>(`/api/accounts/${accountId}/users/${userId}/role`, { role }),

  updateUserRoles: (accountId: number, userId: number, role_codes: string[]) =>
    api.put<{ id: number, role: string, role_codes: string[] }>(`/api/accounts/${accountId}/users/${userId}/roles`, { role_codes }),

  rebindUser: (accountId: number, userId: number, migrate_data: boolean) =>
    api.put(`/api/accounts/${accountId}/users/${userId}`, { migrate_data }),

  createInvite: (accountId: number, expires_in_hours: number) =>
    api.post<{ invite_id: number, invite_code: string, account_id: number, expires_at: string }>(
      `/api/accounts/${accountId}/invites`,
      { expires_in_hours },
    ),

  listInvites: (accountId: number) =>
    api.get<{ items: AccountInvite[], total: number }>(`/api/accounts/${accountId}/invites`),

  revokeInvite: (inviteId: number, reason = '') =>
    api.put(`/api/accounts/invites/${inviteId}/revoke`, { reason }),

  permissions: () => api.get<{ items: PermissionInfo[], total: number }>('/api/accounts/permissions'),

  roles: (accountId?: number) => api.get<{ items: RoleInfo[], total: number }>('/api/accounts/roles', {
    params: accountId ? { account_id: accountId } : undefined,
  }),

  createRole: (accountId: number, data: { code: string, name: string, description: string, permission_codes: string[] }) =>
    api.post<RoleInfo>(`/api/accounts/${accountId}/roles`, data),

  updateRole: (
    accountId: number,
    roleId: number,
    data: { name: string, description: string, status: string, permission_codes: string[] },
  ) => api.put<RoleInfo>(`/api/accounts/${accountId}/roles/${roleId}`, data),

  deleteRole: (accountId: number, roleId: number) =>
    api.delete<{ id: number, deleted: boolean }>(`/api/accounts/${accountId}/roles/${roleId}`),
}

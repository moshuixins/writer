import type {
  AccountInviteListResponse,
  AccountInviteResponse,
  AccountListResponse,
  AccountResponse,
  AccountUsersResponse,
  InviteStatusResponse,
  PermissionListResponse,
  RebindUserResponse,
  RoleDeleteResponse,
  RoleInfoResponse,
  RoleListResponse,
  UserRoleUpdateResponse,
} from '../generated'
import api from '../index'

export default {
  me: () => api.get<AccountResponse>('/api/accounts/me'),

  list: () => api.get<AccountListResponse>('/api/accounts'),

  create: (data: { code: string, name: string }) =>
    api.post<AccountResponse>('/api/accounts', data),

  updateStatus: (accountId: number, status: 'active' | 'disabled') =>
    api.put<AccountResponse>(`/api/accounts/${accountId}/status`, { status }),

  listUsers: (accountId: number) =>
    api.get<AccountUsersResponse>(`/api/accounts/${accountId}/users`),

  updateUserRole: (accountId: number, userId: number, role: string) =>
    api.put<UserRoleUpdateResponse>(`/api/accounts/${accountId}/users/${userId}/role`, { role }),

  updateUserRoles: (accountId: number, userId: number, role_codes: string[]) =>
    api.put<UserRoleUpdateResponse>(`/api/accounts/${accountId}/users/${userId}/roles`, { role_codes }),

  rebindUser: (accountId: number, userId: number, migrate_data: boolean) =>
    api.put<RebindUserResponse>(`/api/accounts/${accountId}/users/${userId}`, { migrate_data }),

  createInvite: (accountId: number, expires_in_hours: number) =>
    api.post<AccountInviteResponse>(`/api/accounts/${accountId}/invites`, { expires_in_hours }),

  listInvites: (accountId: number) =>
    api.get<AccountInviteListResponse>(`/api/accounts/${accountId}/invites`),

  revokeInvite: (inviteId: number, reason = '') =>
    api.put<InviteStatusResponse>(`/api/accounts/invites/${inviteId}/revoke`, { reason }),

  permissions: () => api.get<PermissionListResponse>('/api/accounts/permissions'),

  roles: (accountId?: number) => api.get<RoleListResponse>('/api/accounts/roles', {
    params: accountId ? { account_id: accountId } : undefined,
  }),

  createRole: (accountId: number, data: { code: string, name: string, description: string, permission_codes: string[] }) =>
    api.post<RoleInfoResponse>(`/api/accounts/${accountId}/roles`, data),

  updateRole: (
    accountId: number,
    roleId: number,
    data: { name: string, description: string, status: string, permission_codes: string[] },
  ) => api.put<RoleInfoResponse>(`/api/accounts/${accountId}/roles/${roleId}`, data),

  deleteRole: (accountId: number, roleId: number) =>
    api.delete<RoleDeleteResponse>(`/api/accounts/${accountId}/roles/${roleId}`),
}

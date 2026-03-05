import api from '../index'
import type { Account, AccountInvite, AccountUser, RoleInfo } from '@/types/writer'

export default {
  me: () => api.get<Account>('/api/accounts/me'),

  list: () => api.get<{ items: Account[]; total: number }>('/api/accounts'),

  create: (data: { code: string; name: string }) =>
    api.post<Account>('/api/accounts', data),

  updateStatus: (accountId: number, status: 'active' | 'disabled') =>
    api.put<Account>(`/api/accounts/${accountId}/status`, { status }),

  listUsers: (accountId: number) =>
    api.get<{ account: Account; items: AccountUser[]; total: number }>(`/api/accounts/${accountId}/users`),

  updateUserRole: (accountId: number, userId: number, role: string) =>
    api.put<{ id: number; role: string }>(`/api/accounts/${accountId}/users/${userId}/role`, { role }),

  rebindUser: (accountId: number, userId: number, migrate_data: boolean) =>
    api.put(`/api/accounts/${accountId}/users/${userId}`, { migrate_data }),

  createInvite: (accountId: number, expires_in_hours: number) =>
    api.post<{ invite_id: number; invite_code: string; account_id: number; expires_at: string }>(
      `/api/accounts/${accountId}/invites`,
      { expires_in_hours },
    ),

  listInvites: (accountId: number) =>
    api.get<{ items: AccountInvite[]; total: number }>(`/api/accounts/${accountId}/invites`),

  revokeInvite: (inviteId: number, reason = '') =>
    api.put(`/api/accounts/invites/${inviteId}/revoke`, { reason }),

  roles: () => api.get<{ items: RoleInfo[]; total: number }>('/api/accounts/roles'),
}

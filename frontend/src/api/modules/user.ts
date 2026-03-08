import type { AxiosRequestConfig } from 'axios'
import type {
  AuthTokenResponse,
  AuthUserResponse,
  MessageResponse,
  PermissionCodesResponse,
  ProfileUpdateResponse,
} from '../generated'
import api from '../index'

export default {
  login: (data: { account: string, password: string }) =>
    api.post<AuthTokenResponse>('/api/auth/login', {
      username: data.account,
      password: data.password,
    }),

  register: (data: { username: string, password: string, invite_code: string, display_name?: string }) =>
    api.post<AuthTokenResponse>('/api/auth/register', data),

  permission: () => api.get<PermissionCodesResponse>('/api/auth/permissions'),

  passwordEdit: (data: { password: string, newPassword: string }) =>
    api.post<MessageResponse>('/api/auth/change-password', data),

  getProfile: (config?: AxiosRequestConfig) => api.get<AuthUserResponse>('/api/auth/profile', config),

  updateProfile: (data: { display_name?: string, department?: string }, config?: AxiosRequestConfig) =>
    api.put<ProfileUpdateResponse>('/api/auth/profile', data, config),
}

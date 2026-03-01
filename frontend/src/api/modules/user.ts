import api from '../index'

export default {
  login: (data: { account: string, password: string }) =>
    api.post('/api/auth/login', {
      username: data.account,
      password: data.password,
    }),

  register: (data: { username: string, password: string, display_name?: string }) =>
    api.post('/api/auth/register', data),

  permission: () => Promise.resolve({ data: { permissions: [] } }),

  passwordEdit: (data: { password: string, newPassword: string }) =>
    api.post('/api/auth/change-password', data),

  getProfile: () => api.get('/api/auth/profile'),

  updateProfile: (data: { display_name?: string, department?: string }) =>
    api.put('/api/auth/profile', data),
}

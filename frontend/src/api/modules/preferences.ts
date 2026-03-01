import api from '../index'

export default {
  get: () => api.get('/api/preferences'),

  save: (data: any) => api.put('/api/preferences/batch', data),
}

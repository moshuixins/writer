import api from '../index'

export default {
  exportDoc: (data: any) =>
    api.post('/api/documents/export', data, { responseType: 'blob' }),

  history: () => api.get('/api/documents/history'),

  download: (id: number) =>
    api.get(`/api/documents/history/${id}/download`, { responseType: 'blob' }),
}

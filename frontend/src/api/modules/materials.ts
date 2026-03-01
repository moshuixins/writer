import api from '../index'

export default {
  list: (params: { skip?: number, limit?: number, doc_type?: string, keyword?: string }) =>
    api.get('/api/materials', { params }),

  uploadUrl: '/api/materials/upload',

  delete: (id: number) => api.delete(`/api/materials/${id}`),

  batchDelete: (ids: number[]) => api.post('/api/materials/batch-delete', { ids }),

  batchClassify: (ids: number[], doc_type: string) =>
    api.post('/api/materials/batch-classify', { ids, doc_type }),
}

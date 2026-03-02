import api from '../index'
import type { Material, MaterialListParams, PagedResult } from '@/types/writer'

export default {
  list: (params: MaterialListParams) =>
    api.get<PagedResult<Material>>('/api/materials', { params }),

  uploadUrl: '/api/materials/upload',

  getUploadTask: (taskId: string) =>
    api.get<{
      task_id: string
      status: 'pending' | 'parsing' | 'completed' | 'failed'
      stage: string
      message?: string
      parse_progress: number
      updated_at: number
    }>(`/api/materials/upload-tasks/${taskId}`),

  delete: (id: number) => api.delete(`/api/materials/${id}`),

  batchDelete: (ids: number[]) => api.post('/api/materials/batch-delete', { ids }),

  batchClassify: (ids: number[], doc_type: string) =>
    api.post('/api/materials/batch-classify', { ids, doc_type }),
}

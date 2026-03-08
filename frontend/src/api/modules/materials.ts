import type {
  MaterialListResponse,
  MessageResponse,
  UploadTaskResponse,
} from '../generated'
import type { MaterialListParams } from '@/types/writer'
import api from '../index'

export default {
  list: (params: MaterialListParams) =>
    api.get<MaterialListResponse>('/api/materials', { params }),

  uploadUrl: '/api/materials/upload',

  getUploadTask: (taskId: string) =>
    api.get<UploadTaskResponse>(`/api/materials/upload-tasks/${taskId}`),

  delete: (id: number) => api.delete<MessageResponse>(`/api/materials/${id}`),

  batchDelete: (ids: number[]) => api.post<MessageResponse>('/api/materials/batch-delete', { ids }),

  batchClassify: (ids: number[], doc_type: string) =>
    api.post<MessageResponse>('/api/materials/batch-classify', { ids, doc_type }),
}

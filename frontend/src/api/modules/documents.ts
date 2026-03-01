import api from '../index'
import type { ExportDoc, ExportDocPayload, ExportEditorPayload, PagedResult } from '@/types/writer'

export default {
  exportDoc: (data: ExportDocPayload) =>
    api.post('/api/documents/export', data, { responseType: 'blob' }),

  exportEditorDoc: (data: ExportEditorPayload) =>
    api.post('/api/documents/export-editor', data, { responseType: 'blob' }),

  history: (params: { skip?: number, limit?: number }) =>
    api.get<PagedResult<ExportDoc>>('/api/documents/history', { params }),

  download: (id: number) =>
    api.get(`/api/documents/history/${id}/download`, { responseType: 'blob' }),
}

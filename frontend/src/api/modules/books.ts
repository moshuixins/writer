import type {
  BookImportStartResponse,
  BookImportTaskResponse,
  BookScanResponse,
  BookSourceListResponse,
  BookUploadResponse,
} from '../generated'
import api from '../index'

export default {
  scan: () => api.get<BookScanResponse>('/api/materials/books/scan'),

  uploadBooks: (data: FormData) =>
    api.post<BookUploadResponse>('/api/materials/books/upload', data),

  importBooks: (data: { rebuild?: boolean, selected_files?: string[] }) =>
    api.post<BookImportStartResponse>('/api/materials/books/import', data),

  getTask: (taskId: string) =>
    api.get<BookImportTaskResponse>(`/api/materials/books/tasks/${taskId}`),

  listSources: (params: { skip?: number, limit?: number }) =>
    api.get<BookSourceListResponse>('/api/materials/books/sources', { params }),
}

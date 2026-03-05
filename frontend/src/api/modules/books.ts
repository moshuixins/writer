import api from '../index'
import type { BookImportTask, BookScanItem, BookSourceRecord, PagedResult } from '@/types/writer'

export default {
  scan: () =>
    api.get<{
      books_dir: string
      total: number
      items: BookScanItem[]
    }>('/api/materials/books/scan'),

  importBooks: (data: { rebuild?: boolean, selected_files?: string[] }) =>
    api.post<{
      task_id: string
      status: string
      total_files: number
    }>('/api/materials/books/import', data),

  getTask: (taskId: string) =>
    api.get<BookImportTask>(`/api/materials/books/tasks/${taskId}`),

  listSources: (params: { skip?: number, limit?: number }) =>
    api.get<PagedResult<BookSourceRecord>>('/api/materials/books/sources', { params }),
}

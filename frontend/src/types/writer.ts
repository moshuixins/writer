// Canonical doc_type follows the 79 subtype catalog + "其他" fallback.
export type DocType = string

export interface ChatSession {
  id: number
  title: string
  doc_type: DocType
  status: string
  created_at: string
}

export interface PagedResult<T> {
  items: T[]
  total: number
}

export interface MaterialListParams {
  skip?: number
  limit?: number
  doc_type?: DocType
  keyword?: string
}

export interface ChatMessage {
  id: number | string
  role: string
  content: string
  created_at?: string
  workflow_steps?: ChatWorkflowStep[]
}

export interface ChatWorkflowStep {
  id: string
  step: string
  status: 'running' | 'done' | 'error'
  detail?: string
}

export interface Material {
  id: number
  title: string
  doc_type: DocType
  summary: string
  keywords: string[]
  content_text?: string
  char_count: number
  original_filename?: string
  created_at: string
}

export interface BookScanItem {
  source_name: string
  relative_path: string
  source_hash: string
  file_ext: '.epub' | '.pdf' | string
  file_size: number
  imported: boolean
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed' | string
  doc_type?: string
  updated_at?: string | null
  source_id?: number | null
}

export interface BookImportFileResult {
  source_name: string
  status: 'skipped' | 'completed' | 'partial' | 'failed' | string
  chunk_count: number
  ocr_used: boolean
  ocr_pages: number
  error_message?: string
}

export interface BookImportTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed' | 'interrupted' | string
  stage: string
  message: string
  rebuild: boolean
  started_at: number
  updated_at: number
  finished_at: number | null
  total_files: number
  completed_files: number
  failed_files: number
  partial_files: number
  skipped_files: number
  running_file: string
  file_progress: number
  total_chunks: number
  completed_chunks: number
  chunk_progress: number
  overall_progress: number
  ocr_used_files: number
  ocr_pages: number
  file_results: BookImportFileResult[]
}

export interface BookSourceRecord {
  id: number
  source_name: string
  source_hash: string
  file_ext: string
  file_size: number
  status: string
  doc_type: string
  summary: string
  keywords: string[]
  chunk_count: number
  ocr_used: boolean
  error_message: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ExportDoc {
  id: number
  title: string
  doc_type: DocType
  version: number
  created_at: string
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  department: string
  role?: string
  roles?: string[]
  account_id?: number
}

export interface Account {
  id: number
  code: string
  name: string
  status: string
  user_count?: number
  created_at: string
  updated_at: string
}

export interface UserRoleSummary {
  id: number
  code: string
  name: string
  is_system: boolean
}

export interface AccountUser {
  id: number
  username: string
  display_name: string
  department: string
  role: string
  role_codes: string[]
  roles: UserRoleSummary[]
  created_at: string
}

export interface AccountInvite {
  id: number
  status: string
  created_by?: number | null
  used_by?: number | null
  created_at: string
  used_at?: string | null
  expires_at?: string | null
}

export interface PermissionInfo {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
}

export interface RoleInfo {
  id: number
  account_id: number
  code: string
  role: string
  name: string
  description: string
  status: string
  is_system: boolean
  permissions: string[]
}

export interface Preferences {
  signature_org: string
  default_tone: 'formal' | 'semi-formal'
  default_recipients: string
  avoid_phrases: string
}

export interface ExportDocPayload {
  content_json: Record<string, unknown>
  title: string
  doc_type: DocType
  session_id?: number
}

export interface WriterDraft {
  title: string
  recipients: string
  body_json: Record<string, unknown>
  signing_org: string
  date: string
}

export interface SessionDraftResponse {
  exists: boolean
  session_id: number
  updated_at: string | null
  draft: WriterDraft
}

export interface SaveDraftPayload {
  save_mode: 'auto' | 'manual'
  draft: WriterDraft
}

export interface ExportEditorPayload {
  session_id: number
  doc_type: DocType
  draft: WriterDraft
}

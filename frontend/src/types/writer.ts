export interface ChatSession {
  id: number
  title: string
  doc_type: string
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
  doc_type?: string
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
  doc_type: string
  summary: string
  keywords: string[]
  content_text?: string
  char_count: number
  original_filename?: string
  created_at: string
}

export interface ExportDoc {
  id: number
  title: string
  doc_type: string
  version: number
  created_at: string
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  department: string
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
  doc_type: string
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
  doc_type: string
  draft: WriterDraft
}

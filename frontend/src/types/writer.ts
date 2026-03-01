export interface ChatSession {
  id: number
  title: string
  doc_type: string
  status: string
  created_at: string
}

export interface ChatMessage {
  id: number | string
  role: string
  content: string
  created_at?: string
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

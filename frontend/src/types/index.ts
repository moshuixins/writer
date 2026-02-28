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

export const DOC_TYPES = ['通知', '报告', '请示', '批复', '函', '纪要', '方案', '总结', '讲话稿'] as const

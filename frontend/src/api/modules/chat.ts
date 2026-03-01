import api from '../index'
import type { ChatMessage, ChatSession } from '@/types/writer'

export default {
  getSessions: () => api.get<ChatSession[]>('/api/chat/sessions'),

  createSession: (data: { title: string, doc_type: string | null }) =>
    api.post<ChatSession>('/api/chat/sessions', data),

  updateSession: (sessionId: number, data: { title: string }) =>
    api.put<ChatSession>(`/api/chat/sessions/${sessionId}`, data),

  getMessages: (sessionId: number) =>
    api.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),

  deleteSession: (id: number) => api.delete(`/api/chat/sessions/${id}`),
}

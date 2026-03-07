import type { AxiosRequestConfig } from 'axios'
import type { ChatMessage, ChatSession, SaveDraftPayload, SessionDraftResponse } from '@/types/writer'
import api from '../index'

export default {
  getSessions: () => api.get<ChatSession[]>('/api/chat/sessions'),

  createSession: (data: { title: string, doc_type: string | null }) =>
    api.post<ChatSession>('/api/chat/sessions', data),

  updateSession: (sessionId: number, data: { title: string }) =>
    api.put<ChatSession>(`/api/chat/sessions/${sessionId}`, data),

  getMessages: (sessionId: number) =>
    api.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),

  getDraft: (sessionId: number) =>
    api.get<SessionDraftResponse>(`/api/chat/sessions/${sessionId}/draft`),

  saveDraft: (sessionId: number, data: SaveDraftPayload, config?: AxiosRequestConfig) =>
    api.put<SessionDraftResponse>(`/api/chat/sessions/${sessionId}/draft`, data, config),

  deleteSession: (id: number) => api.delete(`/api/chat/sessions/${id}`),
}

import type { AxiosRequestConfig } from 'axios'
import type {
  ChatMessageListResponse,
  ChatSessionListResponse,
  ChatSessionResponse,
  SessionDraftResponse,
} from '../generated'
import type { SaveDraftPayload } from '@/types/writer'
import api from '../index'

export default {
  getSessions: () => api.get<ChatSessionListResponse>('/api/chat/sessions'),

  createSession: (data: { title: string, doc_type: string | null }) =>
    api.post<ChatSessionResponse>('/api/chat/sessions', data),

  updateSession: (sessionId: number, data: { title: string }) =>
    api.put<ChatSessionResponse>(`/api/chat/sessions/${sessionId}`, data),

  getMessages: (sessionId: number) =>
    api.get<ChatMessageListResponse>(`/api/chat/sessions/${sessionId}/messages`),

  getDraft: (sessionId: number) =>
    api.get<SessionDraftResponse>(`/api/chat/sessions/${sessionId}/draft`),

  saveDraft: (sessionId: number, data: SaveDraftPayload, config?: AxiosRequestConfig) =>
    api.put<SessionDraftResponse>(`/api/chat/sessions/${sessionId}/draft`, data, config),

  deleteSession: (id: number) => api.delete(`/api/chat/sessions/${id}`),
}

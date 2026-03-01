import api from '../index'

export default {
  getSessions: () => api.get('/api/chat/sessions'),

  createSession: (data: { title: string, doc_type: string | null }) =>
    api.post('/api/chat/sessions', data),

  getMessages: (sessionId: number) =>
    api.get(`/api/chat/sessions/${sessionId}/messages`),

  deleteSession: (id: number) => api.delete(`/api/chat/sessions/${id}`),
}

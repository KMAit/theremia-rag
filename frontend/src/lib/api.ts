import axios from 'axios'
import type { Document, Conversation, Message, ModelInfo } from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Unexpected error'
    return Promise.reject(new Error(Array.isArray(msg) ? msg[0]?.msg : msg))
  }
)

// ── Documents ────────────────────────────────────────────────────────────────

export const documentsApi = {
  list: () => api.get<Document[]>('/documents').then((r) => r.data),
  upload: (file: File, onProgress?: (p: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>('/documents', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    }).then((r) => r.data)
  },
  get: (id: string) => api.get<Document>(`/documents/${id}`).then((r) => r.data),
  delete: (id: string) => api.delete(`/documents/${id}`),
}

// ── Conversations ────────────────────────────────────────────────────────────

export const conversationsApi = {
  list: () => api.get<Conversation[]>('/conversations').then((r) => r.data),
  create: (payload: { title?: string; model?: string; document_ids?: string[] }) =>
    api.post<Conversation>('/conversations', payload).then((r) => r.data),
  get: (id: string) => api.get<Conversation>(`/conversations/${id}`).then((r) => r.data),
  update: (id: string, payload: Partial<{ title: string; model: string; document_ids: string[] }>) =>
    api.patch<Conversation>(`/conversations/${id}`, payload).then((r) => r.data),
  delete: (id: string) => api.delete(`/conversations/${id}`),
  models: () => api.get<ModelInfo[]>('/conversations/models').then((r) => r.data),
}

// ── Messages ─────────────────────────────────────────────────────────────────

export const messagesApi = {
  list: (convoId: string) =>
    api.get<Message[]>(`/conversations/${convoId}/messages`).then((r) => r.data),
  ask: (convoId: string, question: string, model?: string) =>
    api.post<Message>(`/conversations/${convoId}/messages`, { question, model }).then((r) => r.data),
}

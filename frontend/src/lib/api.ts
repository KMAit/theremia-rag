import axios from 'axios'
import type { Document, Conversation, Message, ModelInfo } from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 300_000,
})

// ── Error message extractor ──────────────────────────────────────────────────
const extractErrorMessage = (detail: unknown): string => {
  if (Array.isArray(detail)) {
    const first = detail[0]
    return typeof first === 'string' ? first : first?.msg ?? 'Unexpected error'
  }
  return typeof detail === 'string' ? detail : 'Unexpected error'
}

// ── Inject Bearer token ──────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  // Read directly from localStorage to avoid circular import with store
  const raw = localStorage.getItem('theremia-store')
  if (raw) {
    try {
      const { state } = JSON.parse(raw)
      if (state?.token) {
        config.headers.Authorization = `Bearer ${state.token}`
      }
    } catch {
      // Corrupted localStorage — ignore
    }
  }
  return config
})

// ── 401 → logout + reload ────────────────────────────────────────────────────
api.interceptors.response.use(
    (r) => r,
    (err) => {
      if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
        localStorage.removeItem('theremia-store')
        window.location.reload()
        return new Promise(() => {})
      }

      const msg = extractErrorMessage(err.response?.data?.detail) || err.message || 'Unexpected error'
      return Promise.reject(new Error(msg))
    }
)

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
      api.post<{ access_token: string; token_type: string }>(
          '/auth/login',
          new URLSearchParams({ username: email, password }),
          { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      ).then((r) => r.data),

  register: (email: string, password: string) =>
      api.post<{ id: string; email: string }>('/auth/register', { email, password })
          .then((r) => r.data),

  me: () =>
      api.get<{ id: string; email: string }>('/auth/me').then((r) => r.data),
}

// ── Documents ────────────────────────────────────────────────────────────────

export const documentsApi = {
  list: () => api.get<Document[]>('/documents/').then((r) => r.data),
  upload: (file: File, onProgress?: (p: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<Document>('/documents/', form, {
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
  list: () => api.get<Conversation[]>('/conversations/').then((r) => r.data),
  create: (payload: { title?: string; model?: string; document_ids?: string[] }) =>
      api.post<Conversation>('/conversations/', payload).then((r) => r.data),
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
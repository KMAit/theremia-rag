export interface Document {
  id: string
  filename: string
  original_name: string
  size_bytes: number
  page_count: number | null
  chunk_count: number | null
  status: 'processing' | 'ready' | 'error'
  error_message: string | null
  created_at: string
}

export interface SourceChunk {
  doc_id: string
  doc_name: string
  chunk: string
  score: number
  page: number | null
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceChunk[] | null
  tokens_used: number | null
  cost_usd: number | null
  model: string | null
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  model: string
  document_ids: string[]
  total_tokens: number
  total_cost_usd: number
  message_count: number
  created_at: string
  updated_at: string
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  input_cost_per_1k: number
  output_cost_per_1k: number
  context_window: number
}

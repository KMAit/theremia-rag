import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Plus, Settings2, FileText, Zap, DollarSign, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { conversationsApi, messagesApi, documentsApi } from '@/lib/api'
import { useAppStore } from '@/store'
import { cn, formatCost, formatTokens, timeAgo } from '@/lib/utils'
import type { Message, SourceChunk } from '@/types'

export function ChatPage() {
  const qc = useQueryClient()
  const { activeConversationId, setActiveConversation } = useAppStore()
  const [input, setInput] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: conversation } = useQuery({
    queryKey: ['conversation', activeConversationId],
    queryFn: () => conversationsApi.get(activeConversationId!),
    enabled: !!activeConversationId,
  })

  const { data: messages = [] } = useQuery({
    queryKey: ['messages', activeConversationId],
    queryFn: () => messagesApi.list(activeConversationId!),
    enabled: !!activeConversationId,
  })

  const { data: docs = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  })

  const { data: models = [] } = useQuery({
    queryKey: ['models'],
    queryFn: conversationsApi.models,
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => conversationsApi.update(activeConversationId!, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversation', activeConversationId] })
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isAsking])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [input])

  const handleNewConversation = async () => {
    const convo = await conversationsApi.create({ title: 'New conversation' })
    qc.invalidateQueries({ queryKey: ['conversations'] })
    setActiveConversation(convo.id)
  }

  const handleSend = async () => {
    if (!input.trim() || !activeConversationId || isAsking) return
    const q = input.trim()
    setInput('')
    setIsAsking(true)
    try {
      await messagesApi.ask(activeConversationId, q)
      qc.invalidateQueries({ queryKey: ['messages', activeConversationId] })
      qc.invalidateQueries({ queryKey: ['conversation', activeConversationId] })
      qc.invalidateQueries({ queryKey: ['conversations'] })
    } catch (err: any) {
      alert(err.message)
    } finally {
      setIsAsking(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const readyDocs = docs.filter((d) => d.status === 'ready')
  const selectedDocIds = conversation?.document_ids || []

  if (!activeConversationId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center px-8">
        <div className="w-16 h-16 rounded-3xl bg-brand-600 flex items-center justify-center">
          <Zap size={28} className="text-white" />
        </div>
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Start a conversation</h2>
          <p className="text-sm text-ink-muted mt-2 max-w-xs">
            Upload documents and ask questions about them using AI.
          </p>
        </div>
        <button
          onClick={handleNewConversation}
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition-colors"
        >
          <Plus size={16} />
          New conversation
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 h-14 border-b border-surface-200 bg-white flex-shrink-0">
        <h2 className="text-sm font-semibold text-ink truncate max-w-md">
          {conversation?.title || 'Conversation'}
        </h2>
        <div className="flex items-center gap-2">
          {conversation && (
            <div className="flex items-center gap-3 text-xs text-ink-subtle">
              <span className="flex items-center gap-1">
                <Zap size={12} />
                {formatTokens(conversation.total_tokens)} tokens
              </span>
              <span className="flex items-center gap-1">
                <DollarSign size={12} />
                {formatCost(conversation.total_cost_usd)}
              </span>
            </div>
          )}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={cn(
              'p-1.5 rounded-lg transition-colors',
              showSettings ? 'bg-brand-50 text-brand-600' : 'text-ink-subtle hover:bg-surface-100 hover:text-ink'
            )}
          >
            <Settings2 size={16} />
          </button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && conversation && (
        <div className="border-b border-surface-200 bg-surface-50 px-5 py-4 animate-slide-up">
          <div className="flex flex-wrap gap-6">
            {/* Model */}
            <div>
              <label className="text-xs font-medium text-ink-subtle uppercase tracking-wide block mb-1.5">
                Model
              </label>
              <select
                value={conversation.model}
                onChange={(e) => updateMutation.mutate({ model: e.target.value })}
                className="text-sm border border-surface-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} (${m.input_cost_per_1k}/1k in)
                  </option>
                ))}
              </select>
            </div>

            {/* Documents */}
            <div className="flex-1 min-w-48">
              <label className="text-xs font-medium text-ink-subtle uppercase tracking-wide block mb-1.5">
                Documents ({selectedDocIds.length} selected)
              </label>
              {readyDocs.length === 0 ? (
                <p className="text-xs text-ink-subtle">No documents ready. Upload some first.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {readyDocs.map((doc) => {
                    const selected = selectedDocIds.includes(doc.id)
                    return (
                      <button
                        key={doc.id}
                        onClick={() => {
                          const next = selected
                            ? selectedDocIds.filter((id) => id !== doc.id)
                            : [...selectedDocIds, doc.id]
                          updateMutation.mutate({ document_ids: next })
                        }}
                        className={cn(
                          'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors',
                          selected
                            ? 'bg-brand-50 border-brand-300 text-brand-700'
                            : 'bg-white border-surface-200 text-ink-muted hover:border-surface-300'
                        )}
                      >
                        <FileText size={11} />
                        <span className="max-w-[120px] truncate">{doc.original_name}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
        {messages.length === 0 && !isAsking && (
          <div className="text-center text-ink-subtle text-sm py-16">
            <p>Ask a question about your documents.</p>
            {selectedDocIds.length === 0 && (
              <p className="mt-2 text-xs">
                ⚠️ No documents selected. Open settings to attach documents.
              </p>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isAsking && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-surface-200 bg-white flex-shrink-0">
        <div className="flex items-end gap-3 bg-surface-50 border border-surface-200 rounded-2xl px-4 py-3 focus-within:border-brand-400 focus-within:bg-white transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents…"
            rows={1}
            className="flex-1 text-sm text-ink bg-transparent resize-none outline-none placeholder:text-ink-subtle min-h-[22px] max-h-40"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isAsking}
            className={cn(
              'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors',
              input.trim() && !isAsking
                ? 'bg-brand-600 hover:bg-brand-700 text-white'
                : 'bg-surface-200 text-ink-subtle cursor-not-allowed'
            )}
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-[10px] text-ink-subtle mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const [showSources, setShowSources] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3 animate-slide-up', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="w-7 h-7 rounded-xl bg-brand-600 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Zap size={13} className="text-white" />
        </div>
      )}

      <div className={cn('max-w-[70%] space-y-1', isUser ? 'items-end' : 'items-start')}>
        <div className={cn(
          'rounded-2xl px-4 py-3',
          isUser
            ? 'bg-brand-600 text-white rounded-tr-sm'
            : 'bg-white border border-surface-200 text-ink rounded-tl-sm shadow-card'
        )}>
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Meta */}
        <div className={cn('flex items-center gap-2 px-1', isUser ? 'justify-end' : 'justify-start')}>
          <span className="text-[10px] text-ink-subtle">{timeAgo(message.created_at)}</span>
          {message.tokens_used && (
            <span className="text-[10px] text-ink-subtle flex items-center gap-0.5">
              <Zap size={9} />{formatTokens(message.tokens_used)}
            </span>
          )}
          {message.cost_usd && (
            <span className="text-[10px] text-ink-subtle">{formatCost(message.cost_usd)}</span>
          )}
          {message.model && (
            <span className="text-[10px] text-ink-subtle font-mono">{message.model}</span>
          )}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="px-1">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-[11px] text-brand-600 hover:text-brand-700 font-medium"
            >
              <FileText size={11} />
              {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              {showSources ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
            {showSources && (
              <div className="mt-2 space-y-2 animate-slide-up">
                {message.sources.map((src, i) => (
                  <SourceCard key={i} source={src} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({ source }: { source: SourceChunk }) {
  return (
    <div className="bg-surface-50 border border-surface-200 rounded-xl p-3 max-w-sm">
      <div className="flex items-center gap-1.5 mb-1.5">
        <FileText size={11} className="text-brand-500 flex-shrink-0" />
        <span className="text-[11px] font-medium text-ink truncate">{source.doc_name}</span>
        {source.page !== null && (
          <span className="text-[10px] text-ink-subtle ml-auto flex-shrink-0">p.{source.page}</span>
        )}
      </div>
      <p className="text-[11px] text-ink-muted leading-relaxed line-clamp-3">{source.chunk}</p>
      <div className="mt-1.5 text-[10px] text-ink-subtle">
        Score: {(1 - source.score).toFixed(2)}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-7 h-7 rounded-xl bg-brand-600 flex items-center justify-center flex-shrink-0">
        <Zap size={13} className="text-white" />
      </div>
      <div className="bg-white border border-surface-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-card">
        <div className="flex gap-1.5 items-center h-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-slow"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

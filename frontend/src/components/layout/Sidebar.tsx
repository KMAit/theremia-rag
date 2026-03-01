import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, FileText, Plus, Trash2, ChevronLeft, ChevronRight, BrainCircuit } from 'lucide-react'
import { conversationsApi } from '@/lib/api'
import { useAppStore } from '@/store'
import { cn, timeAgo } from '@/lib/utils'
import type { Conversation } from '@/types'

interface SidebarProps {
  view: 'chat' | 'documents'
  onViewChange: (v: 'chat' | 'documents') => void
}

export function Sidebar({ view, onViewChange }: SidebarProps) {
  const qc = useQueryClient()
  const { activeConversationId, setActiveConversation, sidebarOpen, setSidebarOpen } = useAppStore()

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversationsApi.list,
  })

  const createMutation = useMutation({
    mutationFn: () => conversationsApi.create({ title: 'New conversation' }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      setActiveConversation(data.id)
      onViewChange('chat')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      if (activeConversationId === id) setActiveConversation(null)
    },
  })

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-white border-r border-surface-200 transition-all duration-300 ease-in-out',
        sidebarOpen ? 'w-64' : 'w-14'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-surface-200 flex-shrink-0">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <BrainCircuit size={15} className="text-white" />
        </div>
        {sidebarOpen && (
          <span className="font-display font-700 text-ink text-base tracking-tight animate-fade-in">
            Theremia
          </span>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="ml-auto text-ink-subtle hover:text-ink transition-colors"
        >
          {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-2 border-b border-surface-200">
        <NavItem
          icon={<MessageSquare size={16} />}
          label="Chat"
          active={view === 'chat'}
          collapsed={!sidebarOpen}
          onClick={() => onViewChange('chat')}
        />
        <NavItem
          icon={<FileText size={16} />}
          label="Documents"
          active={view === 'documents'}
          collapsed={!sidebarOpen}
          onClick={() => onViewChange('documents')}
        />
      </nav>

      {/* Conversations list */}
      {sidebarOpen && view === 'chat' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2.5">
            <span className="text-xs font-medium text-ink-subtle uppercase tracking-widest">
              Conversations
            </span>
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-surface-100 text-ink-muted hover:text-ink transition-colors"
              title="New conversation"
            >
              <Plus size={14} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
            {conversations.length === 0 && (
              <p className="text-xs text-ink-subtle text-center py-8">
                No conversations yet.<br />Start one!
              </p>
            )}
            {conversations.map((c) => (
              <ConversationItem
                key={c.id}
                conversation={c}
                active={c.id === activeConversationId}
                onSelect={() => { setActiveConversation(c.id); onViewChange('chat') }}
                onDelete={() => deleteMutation.mutate(c.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* New chat button when collapsed */}
      {!sidebarOpen && (
        <div className="p-2 mt-2">
          <button
            onClick={() => createMutation.mutate()}
            className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-100 text-ink-muted hover:text-brand-600 transition-colors"
            title="New conversation"
          >
            <Plus size={16} />
          </button>
        </div>
      )}
    </aside>
  )
}

function NavItem({
  icon, label, active, collapsed, onClick,
}: {
  icon: React.ReactNode
  label: string
  active: boolean
  collapsed: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors w-full text-left',
        active
          ? 'bg-brand-50 text-brand-700'
          : 'text-ink-muted hover:bg-surface-50 hover:text-ink'
      )}
    >
      <span className="flex-shrink-0">{icon}</span>
      {!collapsed && <span>{label}</span>}
    </button>
  )
}

function ConversationItem({
  conversation, active, onSelect, onDelete,
}: {
  conversation: Conversation
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={cn(
        'group flex items-center gap-2 rounded-lg px-2.5 py-2 cursor-pointer transition-colors',
        active ? 'bg-brand-50' : 'hover:bg-surface-50'
      )}
      onClick={onSelect}
    >
      <div className="flex-1 min-w-0">
        <p className={cn('text-xs font-medium truncate', active ? 'text-brand-700' : 'text-ink')}>
          {conversation.title}
        </p>
        <p className="text-[10px] text-ink-subtle mt-0.5">
          {conversation.message_count} msg · {timeAgo(conversation.updated_at)}
        </p>
      </div>
      {hovered && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="flex-shrink-0 text-ink-subtle hover:text-red-500 transition-colors"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}

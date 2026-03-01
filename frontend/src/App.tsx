import { useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { ChatPage } from '@/components/chat/ChatPage'
import { DocumentsPage } from '@/components/documents/DocumentsPage'

type View = 'chat' | 'documents'

export default function App() {
  const [view, setView] = useState<View>('chat')

  return (
    <div className="flex h-screen overflow-hidden bg-surface-50">
      <Sidebar view={view} onViewChange={setView} />
      <main className="flex-1 flex overflow-hidden">
        {view === 'chat' ? <ChatPage /> : <DocumentsPage />}
      </main>
    </div>
  )
}

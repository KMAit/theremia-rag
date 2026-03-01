import { create } from 'zustand'

interface AppStore {
  activeConversationId: string | null
  setActiveConversation: (id: string | null) => void

  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  isPending: boolean
  setPending: (v: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  activeConversationId: null,
  setActiveConversation: (id) => set({ activeConversationId: id }),

  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  isPending: false,
  setPending: (v) => set({ isPending: v }),
}))
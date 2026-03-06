import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
}

interface AppStore {
  // ── Auth ────────────────────────────────────────────────────────────────
  token: string | null
  user: User | null
  setToken: (token: string | null) => void
  setUser: (user: User | null) => void
  logout: () => void

  // ── UI ──────────────────────────────────────────────────────────────────
  activeConversationId: string | null
  setActiveConversation: (id: string | null) => void

  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  isPending: boolean
  setPending: (v: boolean) => void
}

export const useAppStore = create<AppStore>()(
    persist(
        (set) => ({
          // ── Auth ──────────────────────────────────────────────────────────
          token: null,
          user: null,
          setToken: (token) => set({ token }),
          setUser: (user) => set({ user }),
          logout: () => set({ token: null, user: null, activeConversationId: null }),

          // ── UI ────────────────────────────────────────────────────────────
          activeConversationId: null,
          setActiveConversation: (id) => set({ activeConversationId: id }),

          sidebarOpen: true,
          setSidebarOpen: (open) => set({ sidebarOpen: open }),

          isPending: false,
          setPending: (v) => set({ isPending: v }),
        }),
        {
          name: 'theremia-store',
          //  Persist only token + user, not UI state
          partialize: (state) => ({ token: state.token, user: state.user }),
        }
    )
)
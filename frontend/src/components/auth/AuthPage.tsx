import { useState } from 'react'
import { BrainCircuit, Eye, EyeOff, Loader2 } from 'lucide-react'
import { authApi } from '@/lib/api'
import { useAppStore } from '@/store'
import { cn } from '@/lib/utils'

export function AuthPage() {
    const { setToken, setUser } = useAppStore()
    const [mode, setMode] = useState<'login' | 'register'>('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async () => {
        if (!email.trim() || !password.trim()) return
        setLoading(true)
        setError(null)

        try {
            if (mode === 'register') {
                await authApi.register(email.trim(), password)
            }
            const data = await authApi.login(email.trim(), password)
            setToken(data.access_token)
            const me = await authApi.me()
            setUser({ id: me.id, email: me.email })
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Something went wrong')
        } finally {
            setLoading(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') handleSubmit()
    }

    return (
        <div className="min-h-screen bg-surface-50 flex items-center justify-center px-4">
            <div className="w-full max-w-sm animate-fade-in">

                {/* Logo */}
                <div className="flex flex-col items-center mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center mb-4 shadow-card">
                        <BrainCircuit size={22} className="text-white" />
                    </div>
                    <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">Theremia</h1>
                    <p className="text-sm text-ink-subtle mt-1">Document intelligence platform</p>
                </div>

                {/* Card */}
                <div className="bg-white border border-surface-200 rounded-2xl p-6 shadow-card">

                    {/* Toggle */}
                    <div className="flex bg-surface-100 rounded-xl p-1 mb-6">
                        <button
                            onClick={() => { setMode('login'); setError(null) }}
                            className={cn(
                                'flex-1 text-sm font-medium py-1.5 rounded-lg transition-all',
                                mode === 'login'
                                    ? 'bg-white text-ink shadow-card'
                                    : 'text-ink-muted hover:text-ink'
                            )}
                        >
                            Sign in
                        </button>
                        <button
                            onClick={() => { setMode('register'); setError(null) }}
                            className={cn(
                                'flex-1 text-sm font-medium py-1.5 rounded-lg transition-all',
                                mode === 'register'
                                    ? 'bg-white text-ink shadow-card'
                                    : 'text-ink-muted hover:text-ink'
                            )}
                        >
                            Create account
                        </button>
                    </div>

                    {/* Fields */}
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs font-medium text-ink-subtle block mb-1.5">Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="you@example.com"
                                autoComplete="email"
                                className="w-full text-sm border border-surface-200 rounded-xl px-3 py-2.5 bg-white text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
                            />
                        </div>

                        <div>
                            <label className="text-xs font-medium text-ink-subtle block mb-1.5">Password</label>
                            <div className="relative">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="••••••••"
                                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                    className="w-full text-sm border border-surface-200 rounded-xl px-3 py-2.5 pr-10 bg-white text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink transition-colors"
                                >
                                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <p className="mt-3 text-xs text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2 animate-fade-in">
                            {error}
                        </p>
                    )}

                    {/* Submit */}
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !email.trim() || !password.trim()}
                        className={cn(
                            'mt-5 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all',
                            loading || !email.trim() || !password.trim()
                                ? 'bg-surface-200 text-ink-subtle cursor-not-allowed'
                                : 'bg-brand-600 hover:bg-brand-700 text-white shadow-card'
                        )}
                    >
                        {loading && <Loader2 size={15} className="animate-spin" />}
                        {mode === 'login' ? 'Sign in' : 'Create account'}
                    </button>
                </div>
            </div>
        </div>
    )
}
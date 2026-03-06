import { X, AlertCircle, CheckCircle2, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Toast } from '@/hooks/useToast'

interface ToasterProps {
    toasts: Toast[]
    onRemove: (id: number) => void
}

const ICONS = {
    error: AlertCircle,
    success: CheckCircle2,
    info: Info,
}

const STYLES = {
    error: 'bg-red-50 border-red-200 text-red-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
}

const ICON_STYLES = {
    error: 'text-red-500',
    success: 'text-green-500',
    info: 'text-blue-500',
}

export function Toaster({ toasts, onRemove }: ToasterProps) {
    if (toasts.length === 0) return null

    return (
        <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
            {toasts.map((toast) => {
                const Icon = ICONS[toast.type]
                return (
                    <div
                        key={toast.id}
                        className={cn(
                            'flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg',
                            'animate-slide-up pointer-events-auto',
                            STYLES[toast.type]
                        )}
                    >
                        <Icon size={16} className={cn('flex-shrink-0 mt-0.5', ICON_STYLES[toast.type])} />
                        <p className="text-sm flex-1">{toast.message}</p>
                        <button
                            onClick={() => onRemove(toast.id)}
                            className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
                        >
                            <X size={14} />
                        </button>
                    </div>
                )
            })}
        </div>
    )
}
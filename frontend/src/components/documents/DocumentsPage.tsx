import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Trash2, FileText, AlertCircle, CheckCircle2, Clock, RefreshCw } from 'lucide-react'
import { documentsApi } from '@/lib/api'
import { cn, formatBytes, timeAgo } from '@/lib/utils'
import type { Document } from '@/types'

export function DocumentsPage() {
  const qc = useQueryClient()
  const [uploading, setUploading] = useState<{ name: string; progress: number } | null>(null)

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.some((d: Document) => d.status === 'processing')
      return hasProcessing ? 2000 : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })

  const onDrop = useCallback(async (accepted: File[]) => {
    for (const file of accepted) {
      setUploading({ name: file.name, progress: 0 })
      try {
        await documentsApi.upload(file, (p) => setUploading({ name: file.name, progress: p }))
        qc.invalidateQueries({ queryKey: ['documents'] })
      } catch (err: any) {
        alert(err.message)
      } finally {
        setUploading(null)
      }
    }
  }, [qc])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 50 * 1024 * 1024,
    multiple: true,
  })

  const readyCount = docs.filter((d) => d.status === 'ready').length

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-2xl font-semibold text-ink">Documents</h1>
          <p className="text-sm text-ink-muted mt-1">
            Upload PDFs to make them available for Q&A.
            {readyCount > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-green-600 font-medium">
                <CheckCircle2 size={13} />
                {readyCount} ready
              </span>
            )}
          </p>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200',
            isDragActive
              ? 'border-brand-400 bg-brand-50'
              : 'border-surface-300 hover:border-brand-300 hover:bg-surface-50'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className={cn(
              'w-12 h-12 rounded-2xl flex items-center justify-center transition-colors',
              isDragActive ? 'bg-brand-100 text-brand-600' : 'bg-surface-100 text-ink-subtle'
            )}>
              <Upload size={22} />
            </div>
            <div>
              <p className="text-sm font-medium text-ink">
                {isDragActive ? 'Drop to upload' : 'Drop PDFs here or click to browse'}
              </p>
              <p className="text-xs text-ink-subtle mt-1">PDF only · Max 50MB per file</p>
            </div>
          </div>
        </div>

        {/* Upload progress */}
        {uploading && (
          <div className="mt-4 bg-white border border-surface-200 rounded-xl p-4 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <RefreshCw size={14} className="text-brand-600 animate-spin" />
              <span className="text-sm font-medium text-ink truncate flex-1">{uploading.name}</span>
              <span className="text-xs text-ink-muted">{uploading.progress}%</span>
            </div>
            <div className="w-full bg-surface-100 rounded-full h-1.5">
              <div
                className="bg-brand-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${uploading.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Document list */}
        {isLoading ? (
          <div className="mt-8 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-surface-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : docs.length === 0 ? (
          <div className="mt-16 text-center">
            <FileText size={40} className="mx-auto text-surface-300 mb-3" />
            <p className="text-sm text-ink-subtle">No documents yet. Upload your first PDF.</p>
          </div>
        ) : (
          <div className="mt-6 space-y-2">
            {docs.map((doc) => (
              <DocumentRow
                key={doc.id}
                doc={doc}
                onDelete={() => deleteMutation.mutate(doc.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DocumentRow({ doc, onDelete }: { doc: Document; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-3 bg-white border border-surface-200 rounded-xl px-4 py-3 hover:shadow-card-hover transition-shadow animate-fade-in">
      <div className={cn(
        'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
        doc.status === 'ready' ? 'bg-green-50 text-green-600' :
        doc.status === 'error' ? 'bg-red-50 text-red-500' :
        'bg-amber-50 text-amber-500'
      )}>
        {doc.status === 'ready' ? <CheckCircle2 size={16} /> :
         doc.status === 'error' ? <AlertCircle size={16} /> :
         <Clock size={16} />}
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-ink truncate">{doc.original_name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-ink-subtle">{formatBytes(doc.size_bytes)}</span>
          {doc.page_count && (
            <span className="text-xs text-ink-subtle">· {doc.page_count} pages</span>
          )}
          {doc.chunk_count && (
            <span className="text-xs text-ink-subtle">· {doc.chunk_count} chunks</span>
          )}
          <span className="text-xs text-ink-subtle">· {timeAgo(doc.created_at)}</span>
        </div>
        {doc.status === 'processing' && (
          <p className="text-xs text-amber-600 mt-0.5 flex items-center gap-1">
            <RefreshCw size={10} className="animate-spin" /> Indexing…
          </p>
        )}
        {doc.status === 'error' && (
          <p className="text-xs text-red-500 mt-0.5">{doc.error_message}</p>
        )}
      </div>

      <span className={cn(
        'text-[10px] font-medium px-2 py-0.5 rounded-full',
        doc.status === 'ready' ? 'bg-green-50 text-green-700' :
        doc.status === 'error' ? 'bg-red-50 text-red-600' :
        'bg-amber-50 text-amber-700'
      )}>
        {doc.status}
      </span>

      <button
        onClick={onDelete}
        className="text-ink-subtle hover:text-red-500 transition-colors ml-1 flex-shrink-0"
      >
        <Trash2 size={15} />
      </button>
    </div>
  )
}

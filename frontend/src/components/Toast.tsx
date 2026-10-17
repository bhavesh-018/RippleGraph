import { useEffect } from 'react'
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'

export interface ToastMessage {
  id: string
  title: string
  description?: string
  type?: 'success' | 'info' | 'warning'
}

interface ToastProps {
  toasts: ToastMessage[]
  onDismiss: (id: string) => void
}

export default function ToastContainer({ toasts, onDismiss }: ToastProps) {
  if (toasts.length === 0) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss()
    }, 3800)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return (
    <div
      style={{
        pointerEvents: 'auto',
        minWidth: '280px',
        maxWidth: '360px',
        background: '#18181B',
        border: '1px solid #27272A',
        borderRadius: '6px',
        padding: '10px 14px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        animation: 'toast-slide-in 180ms ease-out',
      }}
    >
      <div style={{ marginTop: '2px', flexShrink: 0 }}>
        {toast.type === 'warning' ? (
          <AlertTriangle size={14} color="#F59E0B" />
        ) : toast.type === 'info' ? (
          <Info size={14} color="#A1A1AA" />
        ) : (
          <CheckCircle2 size={14} color="#10B981" />
        )}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#EDEDED' }}>
          {toast.title}
        </span>
        {toast.description && (
          <span style={{ fontSize: '11px', color: '#A1A1AA', fontFamily: 'var(--font-mono)', lineHeight: 1.35 }}>
            {toast.description}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={onDismiss}
        style={{
          background: 'transparent',
          border: 'none',
          color: '#71717A',
          cursor: 'pointer',
          padding: '2px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '3px',
          marginTop: '2px',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#EDEDED')}
        onMouseLeave={(e) => (e.currentTarget.style.color = '#71717A')}
      >
        <X size={12} />
      </button>
    </div>
  )
}

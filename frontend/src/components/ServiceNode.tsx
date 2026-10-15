import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ServiceData, NodeStatus } from '../types'

// ── Status styles ─────────────────────────────────────────────────
const STATUS_STYLES: Record<NodeStatus | 'default', {
  border: string
  stripe: string
  badgeBg: string
  badgeText: string
}> = {
  INCOMPATIBLE: {
    border: 'var(--status-incompatible-border)',
    stripe: 'var(--status-incompatible-text)',
    badgeBg: 'var(--status-incompatible-badge)',
    badgeText: 'var(--status-incompatible-text)',
  },
  COMPATIBLE: {
    border: 'var(--status-compatible-border)',
    stripe: 'var(--status-compatible-text)',
    badgeBg: 'var(--status-compatible-badge)',
    badgeText: 'var(--status-compatible-text)',
  },
  POTENTIAL: {
    border: 'var(--status-potential-border)',
    stripe: 'var(--status-potential-text)',
    badgeBg: 'var(--status-potential-badge)',
    badgeText: 'var(--status-potential-text)',
  },
  EVALUATING: {
    border: '#3A3A3A',
    stripe: '#888888',
    badgeBg: '#2A2A2A',
    badgeText: '#EDEDED',
  },
  UNAFFECTED: {
    border: 'var(--border-subdued)',
    stripe: 'transparent',
    badgeBg: 'var(--border-subdued)',
    badgeText: 'var(--text-muted)',
  },
  default: {
    border: 'var(--border-active)',
    stripe: 'transparent',
    badgeBg: 'var(--border-subdued)',
    badgeText: 'var(--text-muted)',
  },
}

function ServiceNode({ data, selected }: NodeProps<ServiceData>) {
  const isOrigin = data.id === 'auth-service'
  const style = STATUS_STYLES[data.status as NodeStatus] || STATUS_STYLES['default']
  const hasStatus = data.status && data.status !== 'UNAFFECTED'

  return (
    <div
      style={{
        background: isOrigin ? '#F5F5F5' : 'var(--bg-elevated)',
        border: `1px solid ${isOrigin ? '#B0B0B0' : style.border}`,
        borderLeft: isOrigin ? '3px solid #888' : hasStatus ? `3px solid ${style.stripe}` : `1px solid ${style.border}`,
        borderRadius: '6px',
        padding: '10px 14px 10px 12px',
        minWidth: '168px',
        maxWidth: '200px',
        boxShadow: selected ? `0 0 0 1.5px ${style.border}` : '0 1px 4px rgba(0,0,0,0.4)',
        transition: 'border-color 300ms ease, box-shadow 300ms ease',
        cursor: 'default',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#3A3A3A', border: 'none', width: 6, height: 6 }}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>

        {/* Service name */}
        <span style={{
          fontSize: '12px',
          fontWeight: 600,
          color: isOrigin ? '#111' : 'var(--text-primary)',
          lineHeight: 1.3,
          letterSpacing: '-0.01em',
          fontFamily: 'var(--font-sans)',
        }}>
          {data.name}
        </span>

        {/* Status badge row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
          {/* Tier pill */}
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: isOrigin ? '#666' : 'var(--text-muted)',
            background: isOrigin ? '#E0E0E0' : 'var(--border-subdued)',
            padding: '1px 5px',
            borderRadius: '3px',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            T{data.tier}
          </span>

          {/* Status badge — only when set */}
          {hasStatus && (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              fontWeight: 500,
              background: style.badgeBg,
              color: style.badgeText,
              padding: '1px 5px',
              borderRadius: '3px',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}>
              {data.status}
            </span>
          )}
        </div>

        {/* Owner team */}
        <span style={{
          fontSize: '10px',
          color: isOrigin ? '#777' : 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.02em',
          marginTop: '1px',
        }}>
          {data.owner_team}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#3A3A3A', border: 'none', width: 6, height: 6 }}
      />
    </div>
  )
}

export default memo(ServiceNode)

import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { ServiceData, NodeStatus } from '../types'

// ── Status border colors ─────────────────────────────────────────
const STATUS_STYLES: Record<NodeStatus | 'default', { border: string; badgeBg: string; badgeText: string }> = {
  INCOMPATIBLE: {
    border: 'var(--status-incompatible-border)',
    badgeBg: 'var(--status-incompatible-badge)',
    badgeText: 'var(--status-incompatible-text)',
  },
  COMPATIBLE: {
    border: 'var(--status-compatible-border)',
    badgeBg: 'var(--status-compatible-badge)',
    badgeText: 'var(--status-compatible-text)',
  },
  POTENTIAL: {
    border: 'var(--status-potential-border)',
    badgeBg: 'var(--status-potential-badge)',
    badgeText: 'var(--status-potential-text)',
  },
  EVALUATING: {
    border: '#3A3A3A',
    badgeBg: '#2A2A2A',
    badgeText: '#EDEDED',
  },
  UNAFFECTED: {
    border: 'var(--border-subdued)',
    badgeBg: 'var(--border-subdued)',
    badgeText: 'var(--text-muted)',
  },
  default: {
    border: 'var(--border-active)',
    badgeBg: 'var(--border-subdued)',
    badgeText: 'var(--text-muted)',
  },
}

function ServiceNode({ data, selected }: NodeProps<ServiceData>) {
  const isOrigin = data.id === 'auth-service'
  const style = STATUS_STYLES[data.status as NodeStatus] || STATUS_STYLES['default']


  return (
    <div
      style={{
        background: isOrigin ? 'var(--status-origin-bg)' : 'var(--bg-elevated)',
        border: `1px solid ${isOrigin ? '#C0C0C0' : style.border}`,
        borderRadius: '6px',
        padding: '10px 14px',
        minWidth: '148px',
        maxWidth: '180px',
        boxShadow: selected ? `0 0 0 1px ${style.border}` : 'none',
        transition: 'border-color 300ms ease, box-shadow 300ms ease',
        cursor: 'default',
      }}
    >
      {/* Source handle (top) */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#3A3A3A', border: 'none', width: 6, height: 6 }}
      />

      {/* Node content */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>

        {/* Service name */}
        <span style={{
          fontSize: '12px',
          fontWeight: 600,
          color: isOrigin ? 'var(--status-origin-text)' : 'var(--text-primary)',
          lineHeight: 1.3,
          letterSpacing: '-0.01em',
        }}>
          {data.name}
        </span>

        {/* Meta row: tier + status badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
          {/* Tier */}
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: isOrigin ? '#555' : 'var(--text-muted)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            T{data.tier}
          </span>

          {/* Status badge — only shown when status is set */}
          {data.status && data.status !== 'UNAFFECTED' && (
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
        }}>
          {data.owner_team}
        </span>
      </div>

      {/* Target handle (bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#3A3A3A', border: 'none', width: 6, height: 6 }}
      />
    </div>
  )
}

export default memo(ServiceNode)

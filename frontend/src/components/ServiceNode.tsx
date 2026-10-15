import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import {
  Shield,
  CreditCard,
  Users,
  KeyRound,
  ShoppingBag,
  Package,
  Warehouse,
  BarChart3,
  FileText,
  Bell,
  Server,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react'
import type { ServiceData, NodeStatus } from '../types'

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  Shield,
  CreditCard,
  Users,
  KeyRound,
  ShoppingBag,
  Package,
  Warehouse,
  BarChart3,
  FileText,
  Bell,
  Server,
}

function ServiceNode({ data, selected }: NodeProps<ServiceData>) {
  const IconComponent = (data.icon && ICON_MAP[data.icon]) ? ICON_MAP[data.icon] : Server
  const status = (data.status || 'UNAFFECTED').toUpperCase() as NodeStatus
  const isOrigin = Boolean(data.isOrigin)

  // Status visual themes
  let borderColor = '#27272A'
  let statusBadgeBg = '#18181B'
  let statusBadgeText = '#71717A'
  let statusLabel = 'HEALTHY'
  let StatusIcon = CheckCircle2

  if (isOrigin) {
    borderColor = '#6366F1'
    statusBadgeBg = 'rgba(99, 102, 241, 0.15)'
    statusBadgeText = '#A5B4FC'
    statusLabel = 'CHANGE ORIGIN'
    StatusIcon = Server
  } else if (status === 'INCOMPATIBLE') {
    borderColor = '#EF4444'
    statusBadgeBg = 'rgba(239, 68, 68, 0.15)'
    statusBadgeText = '#FCA5A5'
    statusLabel = 'BREAKING'
    StatusIcon = AlertOctagon
  } else if (status === 'POTENTIAL' || status === 'POTENTIAL_DOWNSTREAM') {
    borderColor = '#F59E0B'
    statusBadgeBg = 'rgba(245, 158, 11, 0.15)'
    statusBadgeText = '#FCD34D'
    statusLabel = 'DOWNSTREAM RISK'
    StatusIcon = AlertTriangle
  } else if (status === 'COMPATIBLE') {
    borderColor = '#10B981'
    statusBadgeBg = 'rgba(16, 185, 129, 0.15)'
    statusBadgeText = '#6EE7B7'
    statusLabel = 'COMPATIBLE'
    StatusIcon = CheckCircle2
  } else if (status === 'EVALUATING') {
    borderColor = '#06B6D4'
    statusBadgeBg = 'rgba(6, 182, 212, 0.15)'
    statusBadgeText = '#67E8F9'
    statusLabel = 'EVALUATING...'
    StatusIcon = Server
  }

  // Tier label formatting
  const tierStr = String(data.tier || 'core').toUpperCase()

  return (
    <div
      style={{
        background: '#111113',
        border: `1.5px solid ${borderColor}`,
        borderRadius: '8px',
        padding: '12px 14px',
        width: '240px',
        boxShadow: selected ? '0 0 0 2px #FFFFFF' : '0 1px 4px rgba(0,0,0,0.4)',
        transition: 'all 200ms ease',
        position: 'relative',
        cursor: 'pointer',
      }}
    >
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: borderColor, border: '2px solid #111113', width: 8, height: 8 }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ background: borderColor, border: '2px solid #111113', width: 8, height: 8 }}
      />

      {/* Header Row: Icon + Title + Port */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isOrigin ? '#818CF8' : status === 'INCOMPATIBLE' ? '#F87171' : '#E4E4E7',
            }}
          >
            <IconComponent size={16} />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#F4F4F5', lineHeight: 1.2 }}>
              {data.name || data.id}
            </div>
            {data.port && (
              <span style={{ fontSize: '10px', color: '#71717A', fontFamily: 'var(--font-mono)' }}>
                :{data.port}
              </span>
            )}
          </div>
        </div>

        {/* Status Pill */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '9px',
            fontWeight: 700,
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.04em',
            background: statusBadgeBg,
            color: statusBadgeText,
            padding: '3px 6px',
            borderRadius: '4px',
          }}
        >
          <StatusIcon size={10} />
          <span>{statusLabel}</span>
        </div>
      </div>

      {/* Description */}
      {data.description && (
        <div
          style={{
            fontSize: '11px',
            color: '#A1A1AA',
            lineHeight: 1.35,
            marginBottom: '10px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {data.description}
        </div>
      )}

      {/* Meta Bar: Tier + Runtime + Owner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '10px',
          fontFamily: 'var(--font-mono)',
          paddingTop: '8px',
          borderTop: '1px solid #1F1F23',
          color: '#71717A',
        }}
      >
        <span
          style={{
            background: '#18181B',
            padding: '2px 5px',
            borderRadius: '3px',
            color: '#A1A1AA',
          }}
        >
          {tierStr}
        </span>
        {data.runtime && (
          <span style={{ color: '#A1A1AA' }}>{data.runtime}</span>
        )}
        <span style={{ color: '#52525B' }}>@{data.owner_team}</span>
      </div>

      {/* Outgoing Handles */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: borderColor, border: '2px solid #111113', width: 8, height: 8 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{ background: borderColor, border: '2px solid #111113', width: 8, height: 8 }}
      />
    </div>
  )
}

export default memo(ServiceNode)

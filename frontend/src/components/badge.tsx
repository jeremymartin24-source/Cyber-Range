import type { IncidentSeverity, IncidentStatus, ScenarioDifficulty, ScenarioRunStatus, CampaignRunStatus, CampaignProgressStatus, InjectStatus } from '@/lib/types'

const base = 'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium'

export function SeverityBadge({ severity }: { severity: IncidentSeverity }) {
  const map: Record<IncidentSeverity, string> = {
    low: 'bg-blue-900/50 text-blue-300 border border-blue-800',
    medium: 'bg-yellow-900/50 text-yellow-300 border border-yellow-800',
    high: 'bg-orange-900/50 text-orange-300 border border-orange-800',
    critical: 'bg-red-900/60 text-red-300 border border-red-700',
  }
  return <span className={`${base} ${map[severity]}`}>{severity.toUpperCase()}</span>
}

export function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  const map: Record<IncidentStatus, string> = {
    open: 'bg-red-900/40 text-red-300 border border-red-800',
    investigating: 'bg-yellow-900/40 text-yellow-300 border border-yellow-800',
    contained: 'bg-blue-900/40 text-blue-300 border border-blue-800',
    resolved: 'bg-green-900/40 text-green-300 border border-green-800',
    closed: 'bg-gray-800 text-gray-400 border border-gray-700',
  }
  return <span className={`${base} ${map[status]}`}>{status}</span>
}

export function DifficultyBadge({ difficulty }: { difficulty: ScenarioDifficulty }) {
  const map: Record<ScenarioDifficulty, string> = {
    beginner: 'bg-green-900/40 text-green-300 border border-green-800',
    intermediate: 'bg-yellow-900/40 text-yellow-300 border border-yellow-800',
    advanced: 'bg-orange-900/40 text-orange-300 border border-orange-800',
    expert: 'bg-red-900/40 text-red-300 border border-red-700',
  }
  return <span className={`${base} ${map[difficulty]}`}>{difficulty}</span>
}

export function RunStatusBadge({ status }: { status: ScenarioRunStatus | CampaignRunStatus }) {
  const map: Record<string, string> = {
    active: 'bg-green-900/40 text-green-300 border border-green-800',
    draft: 'bg-gray-800 text-gray-400 border border-gray-700',
    completed: 'bg-blue-900/40 text-blue-300 border border-blue-800',
    aborted: 'bg-red-900/40 text-red-300 border border-red-800',
  }
  return <span className={`${base} ${map[status] ?? 'bg-gray-800 text-gray-400 border border-gray-700'}`}>{status}</span>
}

export function ProgressBadge({ status }: { status: CampaignProgressStatus | string }) {
  const map: Record<string, string> = {
    pending: 'bg-gray-800 text-gray-400 border border-gray-700',
    active: 'bg-yellow-900/40 text-yellow-300 border border-yellow-800',
    completed: 'bg-green-900/40 text-green-300 border border-green-800',
    skipped: 'bg-gray-700 text-gray-500 border border-gray-600',
  }
  return <span className={`${base} ${map[status] ?? 'bg-gray-800 text-gray-400 border border-gray-700'}`}>{status}</span>
}

export function InjectStatusBadge({ status }: { status: InjectStatus }) {
  const map: Record<InjectStatus, string> = {
    pending: 'bg-gray-800 text-gray-400 border border-gray-700',
    fired: 'bg-green-900/40 text-green-300 border border-green-800',
    failed: 'bg-red-900/40 text-red-300 border border-red-800',
    skipped: 'bg-gray-700 text-gray-500 border border-gray-600',
  }
  return <span className={`${base} ${map[status]}`}>{status}</span>
}

export function RuleLevelBadge({ level }: { level: number | null }) {
  if (level === null) return <span className={`${base} bg-gray-800 text-gray-500 border border-gray-700`}>—</span>
  const color =
    level >= 12 ? 'bg-red-900/60 text-red-300 border border-red-700' :
    level >= 8  ? 'bg-orange-900/50 text-orange-300 border border-orange-800' :
    level >= 4  ? 'bg-yellow-900/40 text-yellow-300 border border-yellow-800' :
                  'bg-gray-800 text-gray-400 border border-gray-700'
  return <span className={`${base} ${color}`}>L{level}</span>
}

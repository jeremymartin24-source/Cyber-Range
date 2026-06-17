import { serverApi } from '@/lib/server-api'
import type { Alert } from '@/lib/types'
import { RuleLevelBadge } from '@/components/badge'

function formatDt(dt: string) {
  return new Date(dt).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export default async function AlertsPage() {
  let alerts: Alert[] = []
  try {
    alerts = await serverApi.get<Alert[]>('/api/v1/alerts')
  } catch {
    // handled below
  }

  const unacked = alerts.filter(a => !a.is_acknowledged)
  const acked = alerts.filter(a => a.is_acknowledged)

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Alert Queue</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          {unacked.length} unacknowledged · {alerts.length} total
        </p>
      </div>

      {alerts.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-sm text-gray-500">
          No alerts in queue
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Level</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Description</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Agent</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Groups</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Source</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Timestamp</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Ack</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {alerts.map(a => (
                <tr
                  key={a.id}
                  className={`transition-colors ${a.is_acknowledged ? 'bg-gray-900/50 opacity-60' : 'bg-gray-900 hover:bg-gray-800/50'}`}
                >
                  <td className="px-4 py-3">
                    <RuleLevelBadge level={a.rule_level} />
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-gray-200 truncate">{a.rule_description || '—'}</p>
                    {a.is_simulated && (
                      <span className="text-xs text-purple-400">simulated</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{a.agent_name || '—'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {a.rule_groups.slice(0, 2).join(', ') || '—'}
                    {a.rule_groups.length > 2 && ` +${a.rule_groups.length - 2}`}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {a.is_simulated ? (
                      <span className="text-purple-400">Simulated</span>
                    ) : (
                      <span className="text-gray-400">Wazuh</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{formatDt(a.timestamp)}</td>
                  <td className="px-4 py-3 text-xs">
                    {a.is_acknowledged ? (
                      <span className="text-green-500">✓</span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

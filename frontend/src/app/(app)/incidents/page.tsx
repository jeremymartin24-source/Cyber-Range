import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { Incident } from '@/lib/types'
import { SeverityBadge, IncidentStatusBadge } from '@/components/badge'

function formatDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export default async function IncidentsPage() {
  let incidents: Incident[] = []
  try {
    incidents = await serverApi.get<Incident[]>('/api/v1/incidents')
  } catch {
    // handled below
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Incidents</h1>
          <p className="mt-0.5 text-sm text-gray-500">{incidents.length} total</p>
        </div>
      </div>

      {incidents.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-sm text-gray-500">
          No incidents found
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Number</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {incidents.map(inc => (
                <tr key={inc.id} className="bg-gray-900 hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/incidents/${inc.id}`} className="font-mono text-xs text-blue-400 hover:text-blue-300">
                      {inc.incident_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <Link href={`/incidents/${inc.id}`} className="text-gray-200 hover:text-white truncate block">
                      {inc.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={inc.severity} />
                  </td>
                  <td className="px-4 py-3">
                    <IncidentStatusBadge status={inc.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{inc.category || '—'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{formatDate(inc.detected_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { User, Incident, ScenarioRun, CampaignRun } from '@/lib/types'
import { SeverityBadge, IncidentStatusBadge, RunStatusBadge } from '@/components/badge'

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-100">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-500">{sub}</p>}
    </div>
  )
}

export default async function DashboardPage() {
  const [user, incidents, scenarioRuns, campaignRuns] = await Promise.allSettled([
    serverApi.get<User>('/api/v1/users/me'),
    serverApi.get<Incident[]>('/api/v1/incidents'),
    serverApi.get<ScenarioRun[]>('/api/v1/scenario-runs'),
    serverApi.get<CampaignRun[]>('/api/v1/campaign-runs'),
  ])

  const me = user.status === 'fulfilled' ? user.value : null
  const allIncidents = incidents.status === 'fulfilled' ? incidents.value : []
  const allRuns = scenarioRuns.status === 'fulfilled' ? scenarioRuns.value : []
  const allCampaignRuns = campaignRuns.status === 'fulfilled' ? campaignRuns.value : []

  const openIncidents = allIncidents.filter(i => i.status === 'open' || i.status === 'investigating')
  const activeRuns = allRuns.filter(r => r.status === 'active')
  const activeCampaigns = allCampaignRuns.filter(r => r.status === 'active' || r.status === 'draft')

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">
          {me ? `Welcome back, ${me.first_name}` : 'Dashboard'}
        </h1>
        <p className="mt-0.5 text-sm text-gray-500">Buckeye Manufacturing Group — Security Operations Center</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-8">
        <StatCard label="Open Incidents" value={openIncidents.length} />
        <StatCard label="Total Incidents" value={allIncidents.length} />
        {me?.role !== 'student' && (
          <>
            <StatCard label="Active Runs" value={activeRuns.length} />
            <StatCard label="Campaign Runs" value={activeCampaigns.length} />
          </>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent incidents */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Active Incidents</h2>
            <Link href="/incidents" className="text-xs text-blue-400 hover:text-blue-300">View all →</Link>
          </div>
          <div className="space-y-2">
            {openIncidents.length === 0 && (
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm text-gray-500">
                No active incidents
              </div>
            )}
            {openIncidents.slice(0, 5).map(inc => (
              <Link
                key={inc.id}
                href={`/incidents/${inc.id}`}
                className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 p-3 hover:border-gray-700 hover:bg-gray-800 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-xs text-gray-500 font-mono">{inc.incident_number}</p>
                  <p className="text-sm text-gray-200 truncate mt-0.5">{inc.title}</p>
                </div>
                <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                  <SeverityBadge severity={inc.severity} />
                  <IncidentStatusBadge status={inc.status} />
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Active scenario runs — instructor+ only */}
        {me?.role !== 'student' && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Active Scenario Runs</h2>
              <Link href="/scenarios" className="text-xs text-blue-400 hover:text-blue-300">Manage →</Link>
            </div>
            <div className="space-y-2">
              {activeRuns.length === 0 && (
                <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm text-gray-500">
                  No active runs
                </div>
              )}
              {activeRuns.slice(0, 5).map(run => (
                <Link
                  key={run.id}
                  href={`/scenarios/runs/${run.id}`}
                  className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 p-3 hover:border-gray-700 hover:bg-gray-800 transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-xs text-gray-500 font-mono">{run.id.slice(0, 8)}…</p>
                    <p className="text-sm text-gray-200 mt-0.5">
                      Started {run.started_at ? new Date(run.started_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                  <RunStatusBadge status={run.status} />
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

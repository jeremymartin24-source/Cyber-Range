import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { Scenario, ScenarioRun } from '@/lib/types'
import { DifficultyBadge, RunStatusBadge } from '@/components/badge'
import ScenarioImport from './import-button'

export default async function ScenariosPage() {
  const [scenariosRes, runsRes] = await Promise.allSettled([
    serverApi.get<Scenario[]>('/api/v1/scenarios'),
    serverApi.get<ScenarioRun[]>('/api/v1/scenario-runs'),
  ])

  const scenarios = scenariosRes.status === 'fulfilled' ? scenariosRes.value : []
  const allRuns = runsRes.status === 'fulfilled' ? runsRes.value : []
  const activeRuns = allRuns.filter(r => r.status === 'active')

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Scenarios</h1>
          <p className="mt-0.5 text-sm text-gray-500">{scenarios.length} in library · {activeRuns.length} active runs</p>
        </div>
        <ScenarioImport />
      </div>

      {/* Active runs */}
      {activeRuns.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Active Runs</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {activeRuns.map(run => (
              <Link
                key={run.id}
                href={`/scenarios/runs/${run.id}`}
                className="rounded-lg border border-green-800/40 bg-green-900/10 p-4 hover:bg-green-900/20 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <RunStatusBadge status={run.status} />
                  <span className="text-xs text-gray-500 font-mono">{run.id.slice(0, 8)}…</span>
                </div>
                <p className="text-xs text-gray-500">
                  Started: {run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'}
                </p>
                <p className="text-xs text-blue-400 mt-2">View run →</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Scenario library */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Library</h2>
        {scenarios.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center">
            <p className="text-sm text-gray-500">No scenarios in library.</p>
            <p className="text-xs text-gray-600 mt-1">Import a YAML scenario to get started.</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {scenarios.map(sc => (
              <ScenarioCard key={sc.id} scenario={sc} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function ScenarioCard({ scenario }: { scenario: Scenario }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <DifficultyBadge difficulty={scenario.difficulty} />
          {!scenario.is_active && (
            <span className="text-xs text-gray-600">(inactive)</span>
          )}
        </div>
        <h3 className="text-sm font-semibold text-gray-200">{scenario.name}</h3>
        <p className="text-xs text-gray-500 font-mono mt-0.5">{scenario.slug}</p>
      </div>
      {scenario.description && (
        <p className="text-xs text-gray-400 line-clamp-2">{scenario.description}</p>
      )}
      <div className="flex items-center justify-between text-xs text-gray-500 mt-auto">
        <span>{scenario.estimated_duration_minutes ? `${scenario.estimated_duration_minutes} min` : 'No est.'}</span>
        <span>v{scenario.version}</span>
      </div>
    </div>
  )
}

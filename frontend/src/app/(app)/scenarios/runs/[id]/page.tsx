import { notFound } from 'next/navigation'
import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { ScenarioRun, Scenario, Inject } from '@/lib/types'
import { RunStatusBadge, InjectStatusBadge } from '@/components/badge'
import RunActions from './run-actions'

export default async function ScenarioRunPage({ params }: { params: { id: string } }) {
  let run: ScenarioRun
  try {
    run = await serverApi.get<ScenarioRun>(`/api/v1/scenario-runs/${params.id}`)
  } catch {
    notFound()
  }

  const [scenarioRes, injectsRes] = await Promise.allSettled([
    serverApi.get<Scenario>(`/api/v1/scenarios/${run.scenario_id}`),
    serverApi.get<Inject[]>(`/api/v1/scenario-runs/${params.id}/injects`),
  ])

  const scenario = scenarioRes.status === 'fulfilled' ? scenarioRes.value : null
  const injects = injectsRes.status === 'fulfilled' ? injectsRes.value : []

  const fired = injects.filter(i => i.status === 'fired').length
  const pending = injects.filter(i => i.status === 'pending').length
  const failed = injects.filter(i => i.status === 'failed').length

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <Link href="/scenarios" className="text-xs text-gray-500 hover:text-gray-400 mb-2 block">
          ← Scenarios
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-100">
              {scenario?.name ?? 'Scenario Run'}
            </h1>
            <p className="text-xs font-mono text-gray-500 mt-0.5">{run.id}</p>
          </div>
          <RunStatusBadge status={run.status} />
        </div>
      </div>

      {/* Meta */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Started', value: run.started_at ? new Date(run.started_at).toLocaleString() : '—' },
          { label: 'Completed', value: run.completed_at ? new Date(run.completed_at).toLocaleString() : '—' },
          { label: 'Fired', value: `${fired}/${injects.length}` },
          { label: 'Failed', value: failed },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="mt-0.5 text-sm font-medium text-gray-200">{value}</p>
          </div>
        ))}
      </div>

      {/* Actions */}
      {run.status === 'active' && (
        <div className="mb-6">
          <RunActions runId={run.id} injects={injects} />
        </div>
      )}

      {/* Inject timeline */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
          Inject Timeline ({injects.length})
        </h2>
        {injects.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500 text-center">
            No injects found
          </div>
        ) : (
          <div className="space-y-2">
            {injects.map(inj => (
              <div
                key={inj.id}
                className={`rounded-lg border p-3 ${
                  inj.status === 'fired'
                    ? 'border-green-800/40 bg-green-900/10'
                    : inj.status === 'failed'
                    ? 'border-red-800/40 bg-red-900/10'
                    : 'border-gray-800 bg-gray-900'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <InjectStatusBadge status={inj.status} />
                    <span className="text-sm font-mono text-gray-300">{inj.inject_slug}</span>
                    <span className="text-xs text-gray-500">[{inj.inject_type}]</span>
                  </div>
                  <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                    {inj.fired_at
                      ? `Fired ${new Date(inj.fired_at).toLocaleTimeString()}`
                      : `Sched. ${new Date(inj.scheduled_at).toLocaleTimeString()}`}
                  </span>
                </div>
                {inj.error_message && (
                  <p className="text-xs text-red-400 mt-1">{inj.error_message}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Report link */}
      {run.status !== 'active' && (
        <div className="mt-6">
          <Link
            href={`/reports/runs/${run.id}`}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            View full report →
          </Link>
        </div>
      )}
    </div>
  )
}

import { notFound } from 'next/navigation'
import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { ScenarioRunReport } from '@/lib/types'
import { DifficultyBadge, RunStatusBadge, InjectStatusBadge } from '@/components/badge'

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-3 text-center">
      <p className="text-2xl font-bold text-gray-100">{value}</p>
      <p className="text-xs text-gray-500 uppercase tracking-wide mt-0.5">{label}</p>
    </div>
  )
}

export default async function RunReportPage({ params }: { params: { id: string } }) {
  let report: ScenarioRunReport
  try {
    report = await serverApi.get<ScenarioRunReport>(`/api/v1/scenario-runs/${params.id}/report`)
  } catch {
    notFound()
  }

  const duration = report.duration_minutes != null
    ? `${Math.floor(report.duration_minutes)}m ${Math.round((report.duration_minutes % 1) * 60)}s`
    : '—'

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <Link href="/scenarios" className="text-xs text-gray-500 hover:text-gray-400 mb-2 block">
          ← Scenarios
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-100">{report.scenario_name}</h1>
            <p className="text-xs font-mono text-gray-500 mt-0.5">{report.scenario_slug}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <DifficultyBadge difficulty={report.difficulty as never} />
            <RunStatusBadge status={report.status as never} />
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 mb-8">
        <Stat label="Duration" value={duration} />
        <Stat label="Total Injects" value={report.injects.total} />
        <Stat label="Fired" value={report.injects.fired} />
        <Stat label="Decisions" value={report.decisions.total} />
        <Stat label="Grades" value={report.grades.length} />
      </div>

      {/* Inject stats */}
      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Inject Summary</h2>
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Fired', value: report.injects.fired, color: 'text-green-400' },
            { label: 'Pending', value: report.injects.pending, color: 'text-gray-400' },
            { label: 'Skipped', value: report.injects.skipped, color: 'text-gray-500' },
            { label: 'Failed', value: report.injects.failed, color: 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-3 text-center">
              <p className={`text-lg font-bold ${color}`}>{value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Decision stats */}
      {Object.keys(report.decisions.by_type).length > 0 && (
        <section className="mb-6">
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Decisions by Type</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(report.decisions.by_type).map(([type, count]) => (
              <div key={type} className="rounded border border-gray-800 bg-gray-900 px-3 py-1.5 text-sm">
                <span className="text-gray-400">{type}: </span>
                <span className="font-bold text-gray-200">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Timeline */}
      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
          Timeline ({report.timeline.length} events)
        </h2>
        <div className="space-y-2">
          {report.timeline.length === 0 ? (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm text-gray-500 text-center">
              No timeline events
            </div>
          ) : (
            report.timeline.map((event, i) => (
              <div key={i} className={`flex gap-4 rounded-lg border p-3 ${
                event.event_type === 'inject'
                  ? 'border-blue-800/30 bg-blue-900/10'
                  : 'border-green-800/30 bg-green-900/10'
              }`}>
                <div className="flex-shrink-0 text-xs text-gray-500 w-24 text-right">
                  {new Date(event.occurred_at).toLocaleTimeString()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      event.event_type === 'inject'
                        ? 'bg-blue-900/40 text-blue-300'
                        : 'bg-green-900/40 text-green-300'
                    }`}>
                      {event.event_type}
                    </span>
                    <span className="text-sm text-gray-200">{event.title}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Grades */}
      {report.grades.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Grades ({report.grades.length})
          </h2>
          <div className="overflow-hidden rounded-lg border border-gray-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-900/50">
                  <th className="px-4 py-2 text-left text-xs text-gray-500">Score</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-500">Max</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-500">%</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-500">Feedback</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {report.grades.map(g => (
                  <tr key={g.id} className="bg-gray-900">
                    <td className="px-4 py-2 font-bold text-gray-200">{g.score}</td>
                    <td className="px-4 py-2 text-gray-400">{g.max_score}</td>
                    <td className="px-4 py-2 text-gray-400">
                      {Math.round((g.score / g.max_score) * 100)}%
                    </td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{g.feedback || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

import { notFound } from 'next/navigation'
import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { CampaignRunReport } from '@/lib/types'
import { RunStatusBadge, ProgressBadge } from '@/components/badge'

export default async function CampaignRunReportPage({ params }: { params: { id: string } }) {
  let report: CampaignRunReport
  try {
    report = await serverApi.get<CampaignRunReport>(`/api/v1/campaign-runs/${params.id}/report`)
  } catch {
    notFound()
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <Link href={`/campaigns/runs/${params.id}`} className="text-xs text-gray-500 hover:text-gray-400 mb-2 block">
          ← Campaign Run
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-100">{report.campaign_name}</h1>
            <p className="text-xs font-mono text-gray-500 mt-0.5">{report.campaign_slug}</p>
          </div>
          <RunStatusBadge status={report.status as never} />
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {[
          { label: 'Total Scenarios', value: report.scenarios_total },
          { label: 'Completed', value: report.scenarios_completed },
          { label: 'Pending', value: report.scenarios_pending },
          { label: 'Skipped', value: report.scenarios_skipped },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-3 text-center">
            <p className="text-2xl font-bold text-gray-100">{value}</p>
            <p className="text-xs text-gray-500 uppercase tracking-wide mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Timing */}
      <div className="mb-8 rounded-lg border border-gray-800 bg-gray-900 p-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Started</p>
          <p className="text-gray-200">{report.started_at ? new Date(report.started_at).toLocaleString() : '—'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Completed</p>
          <p className="text-gray-200">{report.completed_at ? new Date(report.completed_at).toLocaleString() : '—'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Total Decisions</p>
          <p className="text-gray-200 font-bold">{report.total_decisions}</p>
        </div>
      </div>

      {/* Scenario breakdown */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Scenario Breakdown</h2>
        <div className="space-y-2">
          {report.scenarios.map(sc => (
            <div
              key={sc.campaign_scenario_entry_id}
              className={`rounded-lg border p-4 ${
                sc.progress_status === 'completed'
                  ? 'border-green-800/40 bg-green-900/10'
                  : sc.progress_status === 'skipped'
                  ? 'border-gray-700 bg-gray-900/50 opacity-60'
                  : 'border-gray-800 bg-gray-900'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-gray-500 w-5 text-right flex-shrink-0">
                    {sc.order_index + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-200">{sc.scenario_name}</p>
                    <p className="text-xs text-gray-500 font-mono">{sc.scenario_slug}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {sc.is_optional && (
                    <span className="text-xs text-gray-500 border border-gray-700 rounded px-1.5 py-0.5">optional</span>
                  )}
                  <ProgressBadge status={sc.progress_status} />
                </div>
              </div>
              {sc.scenario_run_id && (
                <div className="mt-2 ml-8 flex items-center gap-4 text-xs text-gray-500">
                  <span>Run status: {sc.scenario_run_status ?? '—'}</span>
                  <span>Decisions: {sc.decisions_count}</span>
                  <Link
                    href={`/scenarios/runs/${sc.scenario_run_id}`}
                    className="text-blue-400 hover:text-blue-300"
                  >
                    View run →
                  </Link>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

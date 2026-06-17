import { notFound } from 'next/navigation'
import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { CampaignRun, Campaign, CampaignRunProgress } from '@/lib/types'
import { RunStatusBadge, ProgressBadge } from '@/components/badge'
import CampaignRunActions from './run-actions'

export default async function CampaignRunPage({ params }: { params: { id: string } }) {
  let run: CampaignRun
  try {
    run = await serverApi.get<CampaignRun>(`/api/v1/campaign-runs/${params.id}`)
  } catch {
    notFound()
  }

  const [campaignRes, progressRes] = await Promise.allSettled([
    serverApi.get<Campaign>(`/api/v1/campaigns/${run.campaign_id}`),
    serverApi.get<CampaignRunProgress[]>(`/api/v1/campaign-runs/${params.id}/progress`),
  ])

  const campaign = campaignRes.status === 'fulfilled' ? campaignRes.value : null
  const progress = progressRes.status === 'fulfilled' ? progressRes.value : []

  const completed = progress.filter(p => p.status === 'completed').length
  const total = progress.length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <Link href="/campaigns" className="text-xs text-gray-500 hover:text-gray-400 mb-2 block">
          ← Campaigns
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-100">
              {campaign?.name ?? 'Campaign Run'}
            </h1>
            <p className="text-xs font-mono text-gray-500 mt-0.5">{run.id}</p>
          </div>
          <RunStatusBadge status={run.status} />
        </div>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-500">Progress</span>
            <span className="text-xs text-gray-400">{completed}/{total} scenarios completed</span>
          </div>
          <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-500 transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Run meta */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        {[
          { label: 'Started', value: run.started_at ? new Date(run.started_at).toLocaleString() : '—' },
          { label: 'Completed', value: run.completed_at ? new Date(run.completed_at).toLocaleString() : '—' },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="mt-0.5 text-sm text-gray-200">{value}</p>
          </div>
        ))}
      </div>

      {/* Actions (instructor controls) */}
      {(run.status === 'draft' || run.status === 'active') && (
        <div className="mb-6">
          <CampaignRunActions runId={run.id} />
        </div>
      )}

      {/* Scenario progress list */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
          Scenarios ({progress.length})
        </h2>
        {progress.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500 text-center">
            No progress entries found
          </div>
        ) : (
          <div className="space-y-2">
            {progress.map((p, i) => (
              <div
                key={p.id}
                className={`flex items-center gap-4 rounded-lg border p-3 ${
                  p.status === 'completed'
                    ? 'border-green-800/40 bg-green-900/10'
                    : p.status === 'active'
                    ? 'border-yellow-800/40 bg-yellow-900/10'
                    : p.status === 'skipped'
                    ? 'border-gray-700 bg-gray-900/50 opacity-50'
                    : 'border-gray-800 bg-gray-900'
                }`}
              >
                <span className="text-sm font-mono text-gray-500 w-6 text-right flex-shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 font-mono truncate">{p.campaign_scenario_entry_id.slice(0, 8)}…</p>
                  {p.scenario_run_id && (
                    <Link
                      href={`/scenarios/runs/${p.scenario_run_id}`}
                      className="text-xs text-blue-400 hover:text-blue-300 mt-0.5 block"
                    >
                      View scenario run →
                    </Link>
                  )}
                </div>
                <ProgressBadge status={p.status} />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Report link */}
      {run.status === 'completed' && (
        <div className="mt-6">
          <Link
            href={`/campaigns/runs/${run.id}/report`}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            View campaign report →
          </Link>
        </div>
      )}
    </div>
  )
}

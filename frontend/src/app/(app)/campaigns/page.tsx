import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { Campaign, CampaignRun } from '@/lib/types'
import { RunStatusBadge } from '@/components/badge'

export default async function CampaignsPage() {
  const [campaignsRes, runsRes] = await Promise.allSettled([
    serverApi.get<Campaign[]>('/api/v1/campaigns'),
    serverApi.get<CampaignRun[]>('/api/v1/campaign-runs'),
  ])

  const campaigns = campaignsRes.status === 'fulfilled' ? campaignsRes.value : []
  const allRuns = runsRes.status === 'fulfilled' ? runsRes.value : []
  const activeRuns = allRuns.filter(r => r.status === 'active' || r.status === 'draft')

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Campaigns</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          {campaigns.length} in library · {activeRuns.length} active runs
        </p>
      </div>

      {/* Active campaign runs */}
      {activeRuns.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Active Runs</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {activeRuns.map(run => (
              <Link
                key={run.id}
                href={`/campaigns/runs/${run.id}`}
                className="rounded-lg border border-blue-800/30 bg-blue-900/10 p-4 hover:bg-blue-900/20 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <RunStatusBadge status={run.status} />
                  <span className="text-xs text-gray-500 font-mono">{run.id.slice(0, 8)}…</span>
                </div>
                <p className="text-xs text-gray-500">
                  {run.started_at ? `Started ${new Date(run.started_at).toLocaleDateString()}` : 'Not started yet'}
                </p>
                <p className="text-xs text-blue-400 mt-2">View run →</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Campaign library */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">Campaign Library</h2>
        {campaigns.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center">
            <p className="text-sm text-gray-500">No campaigns defined.</p>
            <p className="text-xs text-gray-600 mt-1">Create a campaign to bundle multiple scenarios into a learning arc.</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {campaigns.map(c => (
              <CampaignCard key={c.id} campaign={c} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3">
      <div>
        <div className="flex items-center gap-2 mb-1">
          {!campaign.is_active && (
            <span className="text-xs text-gray-600">(inactive)</span>
          )}
        </div>
        <h3 className="text-sm font-semibold text-gray-200">{campaign.name}</h3>
        <p className="text-xs text-gray-500 font-mono mt-0.5">{campaign.slug}</p>
      </div>
      {campaign.description && (
        <p className="text-xs text-gray-400 line-clamp-2">{campaign.description}</p>
      )}
      <div className="flex items-center justify-between text-xs text-gray-500 mt-auto">
        <span>Created {new Date(campaign.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

export default function CampaignRunActions({ runId }: { runId: string }) {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function act(action: 'launch-next' | 'skip' | 'complete' | 'abort') {
    if (action === 'abort' && !confirm('Abort this campaign run?')) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/v1/campaign-runs/${runId}/${action}`)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : `Failed: ${action}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4 space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Run Controls</p>
      {error && (
        <div className="rounded border border-red-800 bg-red-900/30 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => act('launch-next')}
          disabled={busy}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          Launch Next Scenario
        </button>
        <button
          onClick={() => act('skip')}
          disabled={busy}
          className="rounded-md border border-gray-700 bg-gray-800 px-4 py-1.5 text-xs text-gray-300 hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          Skip
        </button>
        <button
          onClick={() => act('complete')}
          disabled={busy}
          className="rounded-md bg-green-700 px-4 py-1.5 text-xs font-semibold text-white hover:bg-green-600 disabled:opacity-50 transition-colors"
        >
          Complete Run
        </button>
        <button
          onClick={() => act('abort')}
          disabled={busy}
          className="rounded-md border border-red-800 bg-red-900/20 px-4 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-900/40 disabled:opacity-50 transition-colors"
        >
          Abort
        </button>
      </div>
    </div>
  )
}

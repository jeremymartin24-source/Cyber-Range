'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { Inject } from '@/lib/types'
import { api } from '@/lib/api'

export default function RunActions({ runId, injects }: { runId: string; injects: Inject[] }) {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const pendingInjects = injects.filter(i => i.status === 'pending')

  async function fireInject(injectId: string) {
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/v1/scenario-runs/${runId}/injects/${injectId}/fire`)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fire inject')
    } finally {
      setBusy(false)
    }
  }

  async function completeRun() {
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/v1/scenario-runs/${runId}/complete`)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to complete run')
    } finally {
      setBusy(false)
    }
  }

  async function abortRun() {
    if (!confirm('Abort this scenario run?')) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/v1/scenario-runs/${runId}/abort`)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to abort run')
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

      {/* Pending injects to fire */}
      {pendingInjects.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">Fire pending injects:</p>
          <div className="flex flex-wrap gap-2">
            {pendingInjects.map(inj => (
              <button
                key={inj.id}
                onClick={() => fireInject(inj.id)}
                disabled={busy}
                className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 hover:text-gray-100 disabled:opacity-50 font-mono transition-colors"
              >
                Fire: {inj.inject_slug}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={completeRun}
          disabled={busy}
          className="rounded-md bg-green-700 px-4 py-1.5 text-xs font-semibold text-white hover:bg-green-600 disabled:opacity-50 transition-colors"
        >
          Complete Run
        </button>
        <button
          onClick={abortRun}
          disabled={busy}
          className="rounded-md border border-red-800 bg-red-900/20 px-4 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-900/40 disabled:opacity-50 transition-colors"
        >
          Abort Run
        </button>
      </div>
    </div>
  )
}

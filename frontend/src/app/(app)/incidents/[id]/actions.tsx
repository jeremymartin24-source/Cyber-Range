'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { IncidentStatus } from '@/lib/types'
import { api } from '@/lib/api'

const STATUSES: IncidentStatus[] = ['open', 'investigating', 'contained', 'resolved', 'closed']

export default function IncidentActions({
  incidentId,
  currentStatus,
}: {
  incidentId: string
  currentStatus: IncidentStatus
}) {
  const router = useRouter()
  const [showNote, setShowNote] = useState(false)
  const [showDecision, setShowDecision] = useState(false)
  const [noteContent, setNoteContent] = useState('')
  const [decisionTitle, setDecisionTitle] = useState('')
  const [decisionType, setDecisionType] = useState('containment')
  const [decisionRationale, setDecisionRationale] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function changeStatus(status: IncidentStatus) {
    try {
      await api.post(`/api/v1/incidents/${incidentId}/status`, { status })
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update status')
    }
  }

  async function submitNote() {
    if (!noteContent.trim()) return
    setSaving(true)
    setError('')
    try {
      await api.post(`/api/v1/incidents/${incidentId}/notes`, { content: noteContent })
      setNoteContent('')
      setShowNote(false)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save note')
    } finally {
      setSaving(false)
    }
  }

  async function submitDecision() {
    if (!decisionTitle.trim()) return
    setSaving(true)
    setError('')
    try {
      await api.post(`/api/v1/incidents/${incidentId}/decisions`, {
        title: decisionTitle,
        decision_type: decisionType,
        rationale: decisionRationale || undefined,
      })
      setDecisionTitle('')
      setDecisionRationale('')
      setShowDecision(false)
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save decision')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-md border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Status transitions */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500">Status:</span>
        {STATUSES.map(s => (
          <button
            key={s}
            disabled={s === currentStatus}
            onClick={() => changeStatus(s)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              s === currentStatus
                ? 'bg-blue-600 text-white cursor-default'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => { setShowNote(v => !v); setShowDecision(false) }}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 transition-colors"
        >
          + Case Note
        </button>
        <button
          onClick={() => { setShowDecision(v => !v); setShowNote(false) }}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 transition-colors"
        >
          + Decision
        </button>
      </div>

      {/* Case note form */}
      {showNote && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4 space-y-3">
          <p className="text-sm font-medium text-gray-300">Add Case Note</p>
          <textarea
            value={noteContent}
            onChange={e => setNoteContent(e.target.value)}
            rows={3}
            placeholder="Enter your observation or finding…"
            className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={submitNote}
              disabled={saving || !noteContent.trim()}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving…' : 'Save Note'}
            </button>
            <button
              onClick={() => setShowNote(false)}
              className="rounded-md border border-gray-700 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Decision form */}
      {showDecision && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-4 space-y-3">
          <p className="text-sm font-medium text-gray-300">Record Decision</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Title</label>
              <input
                value={decisionTitle}
                onChange={e => setDecisionTitle(e.target.value)}
                placeholder="e.g. Isolate affected host"
                className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={decisionType}
                onChange={e => setDecisionType(e.target.value)}
                className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="containment">Containment</option>
                <option value="eradication">Eradication</option>
                <option value="recovery">Recovery</option>
                <option value="escalation">Escalation</option>
                <option value="evidence_collection">Evidence Collection</option>
                <option value="communication">Communication</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Rationale (optional)</label>
            <textarea
              value={decisionRationale}
              onChange={e => setDecisionRationale(e.target.value)}
              rows={2}
              placeholder="Why was this decision made?"
              className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={submitDecision}
              disabled={saving || !decisionTitle.trim()}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving…' : 'Record Decision'}
            </button>
            <button
              onClick={() => setShowDecision(false)}
              className="rounded-md border border-gray-700 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

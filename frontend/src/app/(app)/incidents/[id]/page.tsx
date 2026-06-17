import { notFound } from 'next/navigation'
import Link from 'next/link'
import { serverApi } from '@/lib/server-api'
import type { Incident, Alert, Evidence, CaseNote, StudentDecision } from '@/lib/types'
import { SeverityBadge, IncidentStatusBadge, RuleLevelBadge } from '@/components/badge'
import IncidentActions from './actions'

function Field({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-200">{value ?? '—'}</dd>
    </div>
  )
}

function formatDt(dt: string | null) {
  if (!dt) return null
  return new Date(dt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default async function IncidentDetailPage({ params }: { params: { id: string } }) {
  let incident: Incident
  try {
    incident = await serverApi.get<Incident>(`/api/v1/incidents/${params.id}`)
  } catch {
    notFound()
  }

  const [alertsRes, evidenceRes, notesRes, decisionsRes] = await Promise.allSettled([
    serverApi.get<Alert[]>(`/api/v1/incidents/${params.id}/alerts`),
    serverApi.get<Evidence[]>(`/api/v1/incidents/${params.id}/evidence`),
    serverApi.get<CaseNote[]>(`/api/v1/incidents/${params.id}/notes`),
    serverApi.get<StudentDecision[]>(`/api/v1/incidents/${params.id}/decisions`),
  ])

  const alerts = alertsRes.status === 'fulfilled' ? alertsRes.value : []
  const evidence = evidenceRes.status === 'fulfilled' ? evidenceRes.value : []
  const notes = notesRes.status === 'fulfilled' ? notesRes.value : []
  const decisions = decisionsRes.status === 'fulfilled' ? decisionsRes.value : []

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <Link href="/incidents" className="text-xs text-gray-500 hover:text-gray-400 mb-2 block">
          ← Incidents
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-mono text-gray-500">{incident.incident_number}</p>
            <h1 className="text-xl font-semibold text-gray-100 mt-0.5">{incident.title}</h1>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <SeverityBadge severity={incident.severity} />
            <IncidentStatusBadge status={incident.status} />
          </div>
        </div>
      </div>

      {/* Meta grid */}
      <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Category" value={incident.category} />
          <Field label="Detected" value={formatDt(incident.detected_at)} />
          <Field label="Contained" value={formatDt(incident.contained_at)} />
          <Field label="Resolved" value={formatDt(incident.resolved_at)} />
        </dl>
        {incident.description && (
          <div className="mt-4 border-t border-gray-800 pt-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Description</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap">{incident.description}</p>
          </div>
        )}
      </div>

      {/* Client-side actions (status change, add note, add decision) */}
      <IncidentActions incidentId={incident.id} currentStatus={incident.status} />

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Alerts */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Alerts ({alerts.length})
          </h2>
          <div className="space-y-2">
            {alerts.length === 0 && (
              <p className="text-sm text-gray-600 rounded-lg border border-gray-800 bg-gray-900 p-3">No alerts linked</p>
            )}
            {alerts.map(a => (
              <div key={a.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono text-gray-500">{a.rule_id ?? '—'}</span>
                  <div className="flex gap-1.5">
                    <RuleLevelBadge level={a.rule_level} />
                    {a.is_simulated && (
                      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-purple-900/40 text-purple-300 border border-purple-800">
                        sim
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-gray-200">{a.rule_description || 'No description'}</p>
                {a.agent_name && <p className="text-xs text-gray-500 mt-0.5">Agent: {a.agent_name}</p>}
                <p className="text-xs text-gray-600 mt-1">{new Date(a.timestamp).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Evidence */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Evidence ({evidence.length})
          </h2>
          <div className="space-y-2">
            {evidence.length === 0 && (
              <p className="text-sm text-gray-600 rounded-lg border border-gray-800 bg-gray-900 p-3">No evidence submitted</p>
            )}
            {evidence.map(e => (
              <div key={e.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-gray-300">{e.title}</span>
                  <span className="text-xs text-gray-500">{e.evidence_type}</span>
                </div>
                {e.description && <p className="text-sm text-gray-400">{e.description}</p>}
                {e.artifact && (
                  <p className="text-xs font-mono text-gray-500 mt-1 truncate">{e.artifact}</p>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Case Notes */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Case Notes ({notes.length})
          </h2>
          <div className="space-y-2">
            {notes.length === 0 && (
              <p className="text-sm text-gray-600 rounded-lg border border-gray-800 bg-gray-900 p-3">No case notes</p>
            )}
            {notes.map(n => (
              <div key={n.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                <p className="text-sm text-gray-200 whitespace-pre-wrap">{n.content}</p>
                <p className="text-xs text-gray-500 mt-2">{new Date(n.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Student Decisions */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Decisions ({decisions.length})
          </h2>
          <div className="space-y-2">
            {decisions.length === 0 && (
              <p className="text-sm text-gray-600 rounded-lg border border-gray-800 bg-gray-900 p-3">No decisions recorded</p>
            )}
            {decisions.map(d => (
              <div key={d.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-gray-300">{d.title}</span>
                  <span className="text-xs text-gray-500">{d.decision_type}</span>
                </div>
                {d.rationale && <p className="text-sm text-gray-400 mt-1">{d.rationale}</p>}
                <p className="text-xs text-gray-600 mt-1">{new Date(d.occurred_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

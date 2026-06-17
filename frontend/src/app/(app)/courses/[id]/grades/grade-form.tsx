'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import type { CourseLeaderboardEntry } from '@/lib/types'

interface Props {
  runId: string
  courseId: string
  students: CourseLeaderboardEntry[]
}

export function GradeForm({ runId, students }: Props) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const [studentId, setStudentId] = useState('')
  const [score, setScore] = useState('')
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!studentId || !score) return
    setError(null)
    setSuccess(false)

    const numScore = parseFloat(score)
    if (isNaN(numScore) || numScore < 0 || numScore > 100) {
      setError('Score must be a number between 0 and 100')
      return
    }

    try {
      const res = await fetch(`/api/v1/scenario-runs/${runId}/grades`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          score: numScore,
          max_score: 100,
          feedback: feedback || null,
          rubric: {},
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to save grade')
        return
      }
      setSuccess(true)
      setStudentId('')
      setScore('')
      setFeedback('')
      startTransition(() => router.refresh())
    } catch {
      setError('Network error')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Add grade</p>
      <div className="flex flex-wrap gap-3">
        <select
          value={studentId}
          onChange={e => setStudentId(e.target.value)}
          required
          className="flex-1 min-w-[200px] rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">— Select student —</option>
          {students.map(s => (
            <option key={s.student_id} value={s.student_id}>
              {s.student_name} ({s.student_email})
            </option>
          ))}
        </select>

        <input
          type="number"
          min={0}
          max={100}
          step={0.5}
          placeholder="Score /100"
          value={score}
          onChange={e => setScore(e.target.value)}
          required
          className="w-32 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <textarea
        placeholder="Feedback (optional)"
        value={feedback}
        onChange={e => setFeedback(e.target.value)}
        rows={2}
        className="w-full rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
      />

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!studentId || !score || isPending}
          className="px-4 py-2 text-sm rounded bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPending ? 'Saving…' : 'Save grade'}
        </button>
        {success && <span className="text-xs text-green-400">Grade saved!</span>}
        {error && <span className="text-xs text-red-400">{error}</span>}
      </div>
    </form>
  )
}

'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import type { User } from '@/lib/types'

interface Props {
  courseId: string
  enrolledUsers: User[]
  availableUsers: User[]
}

export function EnrollActions({ courseId, enrolledUsers, availableUsers }: Props) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const [selectedUserId, setSelectedUserId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  async function handleEnroll() {
    if (!selectedUserId) return
    setError(null)
    try {
      const res = await fetch(`/api/v1/courses/${courseId}/enroll`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: selectedUserId }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to enroll student')
        return
      }
      setSelectedUserId('')
      startTransition(() => router.refresh())
    } catch {
      setError('Network error')
    }
  }

  async function handleRemove(userId: string) {
    setRemoving(userId)
    setError(null)
    try {
      const res = await fetch(`/api/v1/courses/${courseId}/enrollments/${userId}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to remove student')
        return
      }
      startTransition(() => router.refresh())
    } catch {
      setError('Network error')
    } finally {
      setRemoving(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* Enrolled list */}
      {enrolledUsers.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-sm text-gray-500">
          No students enrolled yet
        </div>
      ) : (
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-900 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-2.5 text-left">Name</th>
                <th className="px-4 py-2.5 text-left">Email</th>
                <th className="px-4 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {enrolledUsers.map(u => (
                <tr key={u.id} className="bg-gray-950 hover:bg-gray-900 transition-colors">
                  <td className="px-4 py-3 text-gray-200">
                    {u.first_name} {u.last_name}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{u.email}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRemove(u.id)}
                      disabled={removing === u.id || isPending}
                      className="text-xs text-red-500 hover:text-red-400 disabled:opacity-40"
                    >
                      {removing === u.id ? 'Removing…' : 'Remove'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add student row */}
      {availableUsers.length > 0 && (
        <div className="flex items-center gap-3">
          <select
            value={selectedUserId}
            onChange={e => setSelectedUserId(e.target.value)}
            className="flex-1 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">— Select a student to enroll —</option>
            {availableUsers.map(u => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name} ({u.email})
              </option>
            ))}
          </select>
          <button
            onClick={handleEnroll}
            disabled={!selectedUserId || isPending}
            className="px-4 py-2 text-sm rounded bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            Enroll
          </button>
        </div>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}

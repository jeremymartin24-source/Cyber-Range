import Link from 'next/link'
import { redirect } from 'next/navigation'
import { serverApi } from '@/lib/server-api'
import type { Course, EnrollmentResponse, PaginatedUsers, ScenarioRun, User } from '@/lib/types'
import { RunStatusBadge } from '@/components/badge'
import { EnrollActions } from './enroll-actions'

interface Props {
  params: { id: string }
}

export default async function CourseDetailPage({ params }: Props) {
  let me: User
  try {
    me = await serverApi.get<User>('/api/v1/auth/me')
  } catch {
    redirect('/login')
  }

  if (me.role === 'student') redirect('/courses')

  const [course, enrollments, usersPage, runs] = await Promise.all([
    serverApi.get<Course>(`/api/v1/courses/${params.id}`).catch(() => null),
    serverApi
      .get<EnrollmentResponse[]>(`/api/v1/courses/${params.id}/enrollments`)
      .catch(() => [] as EnrollmentResponse[]),
    serverApi
      .get<PaginatedUsers>('/api/v1/users/?limit=200')
      .catch(() => ({ items: [] as User[], total: 0, limit: 200, offset: 0 })),
    serverApi
      .get<ScenarioRun[]>(`/api/v1/scenario-runs?course_id=${params.id}`)
      .catch(() => [] as ScenarioRun[]),
  ])

  if (!course) {
    return (
      <div className="p-6 text-sm text-gray-500">Course not found.</div>
    )
  }

  const enrolledIds = new Set(enrollments.map(e => e.user_id))
  const enrolledUsers = usersPage.items.filter(u => enrolledIds.has(u.id))
  const availableUsers = usersPage.items.filter(
    u => !enrolledIds.has(u.id) && u.role === 'student',
  )

  const label = [course.semester, course.year].filter(Boolean).join(' ')

  return (
    <div className="p-6 space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link href="/courses" className="text-xs text-gray-500 hover:text-gray-300">
            ← Courses
          </Link>
          {label && <span className="text-xs text-gray-600">/ {label}</span>}
        </div>
        <h1 className="text-xl font-semibold text-gray-100">{course.name}</h1>
        {course.description && (
          <p className="mt-1 text-sm text-gray-400">{course.description}</p>
        )}
      </div>

      {/* Enrollments */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
            Enrolled Students
            <span className="ml-2 text-gray-500 font-normal normal-case">
              {enrolledUsers.length}
            </span>
          </h2>
          <Link
            href={`/courses/${params.id}/grades`}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            View grades →
          </Link>
        </div>

        <EnrollActions
          courseId={params.id}
          enrolledUsers={enrolledUsers}
          availableUsers={availableUsers}
        />
      </section>

      {/* Scenario Runs */}
      <section>
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Scenario Runs
          <span className="ml-2 text-gray-500 font-normal normal-case">{runs.length}</span>
        </h2>

        {runs.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-sm text-gray-500">
            No runs yet — launch a scenario from the{' '}
            <Link href="/scenarios" className="text-indigo-400 hover:text-indigo-300">
              Scenarios
            </Link>{' '}
            page.
          </div>
        ) : (
          <div className="rounded-lg border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-900 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2.5 text-left">Run ID</th>
                  <th className="px-4 py-2.5 text-left">Status</th>
                  <th className="px-4 py-2.5 text-left">Started</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {runs.map(run => (
                  <tr key={run.id} className="bg-gray-950 hover:bg-gray-900 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {run.id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3">
                      <RunStatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString()
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/scenarios/runs/${run.id}`}
                        className="text-xs text-indigo-400 hover:text-indigo-300"
                      >
                        Details →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

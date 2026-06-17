import Link from 'next/link'
import { redirect } from 'next/navigation'
import { serverApi } from '@/lib/server-api'
import type {
  Course,
  CourseLeaderboardEntry,
  GradeResponse,
  ScenarioRun,
  User,
} from '@/lib/types'
import { GradeForm } from './grade-form'

interface Props {
  params: { id: string }
}

export default async function CourseGradesPage({ params }: Props) {
  let me: User
  try {
    me = await serverApi.get<User>('/api/v1/auth/me')
  } catch {
    redirect('/login')
  }

  if (me.role === 'student') redirect('/courses')

  const [course, leaderboard, grades, runs] = await Promise.all([
    serverApi.get<Course>(`/api/v1/courses/${params.id}`).catch(() => null),
    serverApi
      .get<CourseLeaderboardEntry[]>(`/api/v1/courses/${params.id}/leaderboard`)
      .catch(() => [] as CourseLeaderboardEntry[]),
    serverApi
      .get<GradeResponse[]>(`/api/v1/courses/${params.id}/grades`)
      .catch(() => [] as GradeResponse[]),
    serverApi
      .get<ScenarioRun[]>(`/api/v1/scenario-runs?course_id=${params.id}`)
      .catch(() => [] as ScenarioRun[]),
  ])

  if (!course) {
    return <div className="p-6 text-sm text-gray-500">Course not found.</div>
  }

  // Build a lookup: runId → grade[] for quick access
  const gradesByRun = new Map<string, GradeResponse[]>()
  for (const g of grades) {
    const list = gradesByRun.get(g.scenario_run_id) ?? []
    list.push(g)
    gradesByRun.set(g.scenario_run_id, list)
  }

  const completedRuns = runs.filter(r => r.status === 'completed')

  return (
    <div className="p-6 space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link href="/courses" className="text-xs text-gray-500 hover:text-gray-300">
            ← Courses
          </Link>
          <span className="text-xs text-gray-600">/</span>
          <Link
            href={`/courses/${params.id}`}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            {course.name}
          </Link>
          <span className="text-xs text-gray-600">/ Grades</span>
        </div>
        <h1 className="text-xl font-semibold text-gray-100">Grade Overview</h1>
        <p className="mt-0.5 text-sm text-gray-500">{course.name}</p>
      </div>

      {/* Leaderboard */}
      <section>
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Leaderboard
        </h2>
        {leaderboard.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-sm text-gray-500">
            No grades recorded yet
          </div>
        ) : (
          <div className="rounded-lg border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-900 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2.5 text-left">#</th>
                  <th className="px-4 py-2.5 text-left">Student</th>
                  <th className="px-4 py-2.5 text-center">Runs graded</th>
                  <th className="px-4 py-2.5 text-center">Avg score</th>
                  <th className="px-4 py-2.5 text-center">Best</th>
                  <th className="px-4 py-2.5 text-center">Decisions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {leaderboard.map((entry, idx) => (
                  <tr key={entry.student_id} className="bg-gray-950 hover:bg-gray-900 transition-colors">
                    <td className="px-4 py-3 text-gray-500 text-xs">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <div className="text-gray-200 font-medium">{entry.student_name}</div>
                      <div className="text-xs text-gray-500">{entry.student_email}</div>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-300">{entry.runs_graded}</td>
                    <td className="px-4 py-3 text-center">
                      <ScoreChip score={entry.average_score} max={100} />
                    </td>
                    <td className="px-4 py-3 text-center text-gray-300">
                      {entry.highest_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-400">{entry.total_decisions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Per-run grade entry */}
      <section>
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
          Grade Entry
          <span className="ml-2 text-gray-500 font-normal normal-case text-xs">
            completed runs only
          </span>
        </h2>

        {completedRuns.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-sm text-gray-500">
            No completed scenario runs in this course yet
          </div>
        ) : (
          <div className="space-y-4">
            {completedRuns.map(run => {
              const runGrades = gradesByRun.get(run.id) ?? []
              return (
                <RunGradePanel
                  key={run.id}
                  run={run}
                  courseId={params.id}
                  existingGrades={runGrades}
                  leaderboard={leaderboard}
                />
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

function ScoreChip({ score, max }: { score: number; max: number }) {
  const pct = (score / max) * 100
  const color =
    pct >= 90
      ? 'text-green-400'
      : pct >= 75
        ? 'text-yellow-400'
        : pct >= 60
          ? 'text-orange-400'
          : 'text-red-400'
  return <span className={`font-mono font-semibold ${color}`}>{score.toFixed(1)}</span>
}

function RunGradePanel({
  run,
  courseId,
  existingGrades,
  leaderboard,
}: {
  run: ScenarioRun
  courseId: string
  existingGrades: GradeResponse[]
  leaderboard: CourseLeaderboardEntry[]
}) {
  const gradedIds = new Set(existingGrades.map(g => g.student_id))
  const ungradedStudents = leaderboard.filter(e => !gradedIds.has(e.student_id))

  return (
    <div className="rounded-lg border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-gray-500">{run.id.slice(0, 8)}…</span>
          <span className="text-xs text-gray-400">
            Completed {run.completed_at ? new Date(run.completed_at).toLocaleDateString() : ''}
          </span>
        </div>
        <Link
          href={`/scenarios/runs/${run.id}`}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          View run →
        </Link>
      </div>

      {/* Existing grades */}
      {existingGrades.length > 0 && (
        <div className="divide-y divide-gray-800">
          {existingGrades.map(g => (
            <div key={g.id} className="flex items-center justify-between px-4 py-2.5 bg-gray-950">
              <div className="text-sm text-gray-300">
                {leaderboard.find(e => e.student_id === g.student_id)?.student_name ??
                  g.student_id.slice(0, 8)}
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm font-mono text-gray-200">
                  {g.score}/{g.max_score}
                </span>
                {g.feedback && (
                  <span className="text-xs text-gray-500 max-w-xs truncate">{g.feedback}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Grade entry form for ungraded students */}
      {ungradedStudents.length > 0 && (
        <div className="px-4 py-3 bg-gray-950 border-t border-gray-800">
          <GradeForm runId={run.id} courseId={courseId} students={ungradedStudents} />
        </div>
      )}
    </div>
  )
}

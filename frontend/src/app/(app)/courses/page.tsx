import { serverApi } from '@/lib/server-api'
import type { Course } from '@/lib/types'

export default async function CoursesPage() {
  let courses: Course[] = []
  try {
    courses = await serverApi.get<Course[]>('/api/v1/courses')
  } catch {
    // handled below
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Courses</h1>
        <p className="mt-0.5 text-sm text-gray-500">{courses.length} courses</p>
      </div>

      {courses.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-sm text-gray-500">
          No courses found
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map(c => (
            <CourseCard key={c.id} course={c} />
          ))}
        </div>
      )}
    </div>
  )
}

function CourseCard({ course }: { course: Course }) {
  const label = [course.semester, course.year].filter(Boolean).join(' ')
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3">
      <div>
        <div className="flex items-center gap-2 mb-1">
          {!course.is_active && (
            <span className="text-xs text-gray-600 border border-gray-700 rounded px-1.5 py-0.5">inactive</span>
          )}
          {label && <span className="text-xs text-gray-500">{label}</span>}
        </div>
        <h3 className="text-sm font-semibold text-gray-200">{course.name}</h3>
      </div>
      {course.description && (
        <p className="text-xs text-gray-400 line-clamp-2">{course.description}</p>
      )}
      <div className="flex items-center justify-between text-xs text-gray-500 mt-auto pt-1 border-t border-gray-800">
        <span>Created {new Date(course.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  )
}

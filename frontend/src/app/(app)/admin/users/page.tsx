import { serverApi } from '@/lib/server-api'
import type { User, PaginatedUsers } from '@/lib/types'

const ROLE_COLORS: Record<string, string> = {
  admin: 'text-red-400',
  instructor: 'text-yellow-400',
  student: 'text-blue-400',
}

export default async function UsersPage() {
  let users: User[] = []
  try {
    const data = await serverApi.get<PaginatedUsers>('/api/v1/users')
    users = data.items
  } catch {
    // handled below
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Users</h1>
        <p className="mt-0.5 text-sm text-gray-500">{users.length} total</p>
      </div>

      {users.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-sm text-gray-500">
          No users found
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {users.map(u => (
                <tr key={u.id} className={`bg-gray-900 hover:bg-gray-800/50 transition-colors ${!u.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 text-gray-200">
                    {u.first_name} {u.last_name}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs font-mono">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${ROLE_COLORS[u.role] ?? 'text-gray-400'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${u.is_active ? 'text-green-500' : 'text-gray-500'}`}>
                      {u.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

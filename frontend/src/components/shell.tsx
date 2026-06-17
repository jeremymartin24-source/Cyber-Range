'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import type { User } from '@/lib/types'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: '⬡', roles: ['admin', 'instructor', 'student'] },
  { href: '/incidents', label: 'Incidents', icon: '⚠', roles: ['admin', 'instructor', 'student'] },
  { href: '/alerts', label: 'Alerts', icon: '◉', roles: ['admin', 'instructor', 'student'] },
  { href: '/scenarios', label: 'Scenarios', icon: '▶', roles: ['admin', 'instructor'] },
  { href: '/campaigns', label: 'Campaigns', icon: '⊞', roles: ['admin', 'instructor'] },
  { href: '/courses', label: 'Courses', icon: '≡', roles: ['admin', 'instructor', 'student'] },
  { href: '/admin/users', label: 'Users', icon: '◎', roles: ['admin'] },
] as const

function NavItem({ href, label, icon }: { href: string; label: string; icon: string }) {
  const pathname = usePathname()
  const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
        active
          ? 'bg-blue-600/20 text-blue-400 font-medium'
          : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
      }`}
    >
      <span className="w-4 text-center font-mono text-xs">{icon}</span>
      {label}
    </Link>
  )
}

export default function Shell({ user, children }: { user: User; children: React.ReactNode }) {
  const router = useRouter()

  async function handleLogout() {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
    router.push('/login')
  }

  const visibleItems = NAV_ITEMS.filter(item => (item.roles as readonly string[]).includes(user.role))

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Sidebar */}
      <aside className="flex w-56 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-950">
        {/* Brand */}
        <div className="flex h-14 items-center border-b border-gray-800 px-4">
          <span className="text-sm font-bold tracking-widest text-blue-400 uppercase">CyberOps</span>
          <span className="ml-1 text-sm font-bold tracking-widest text-gray-500 uppercase">Range</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {visibleItems.map(item => (
            <NavItem key={item.href} href={item.href} label={item.label} icon={item.icon} />
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-800 p-3">
          <div className="mb-2 px-2">
            <p className="text-sm font-medium text-gray-200 truncate">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-xs text-gray-500 truncate">{user.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full rounded-md px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors text-left"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  )
}

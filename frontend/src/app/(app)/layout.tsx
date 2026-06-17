import { redirect } from 'next/navigation'
import { serverApi } from '@/lib/server-api'
import type { User } from '@/lib/types'
import Shell from '@/components/shell'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  let user: User
  try {
    user = await serverApi.get<User>('/api/v1/users/me')
  } catch {
    redirect('/login')
  }

  return <Shell user={user}>{children}</Shell>
}

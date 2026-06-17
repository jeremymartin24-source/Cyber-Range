import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

// Internal URL for server-side fetches (Docker internal network or localhost for dev)
const INTERNAL_API = process.env.INTERNAL_API_URL || 'http://backend:8000'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function serverRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const cookieStore = cookies()
  const token = cookieStore.get('access_token')?.value

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Cookie: `access_token=${token}` } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  }

  const res = await fetch(`${INTERNAL_API}${path}`, {
    ...options,
    headers,
    cache: 'no-store',
  })

  if (res.status === 401) {
    redirect('/login')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, error.detail || 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const serverApi = {
  get: <T>(path: string) => serverRequest<T>(path),
  post: <T>(path: string, body?: unknown) =>
    serverRequest<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    serverRequest<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => serverRequest<T>(path, { method: 'DELETE' }),
}

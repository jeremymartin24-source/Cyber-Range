const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

interface ApiOptions extends RequestInit {
  json?: unknown
}

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, ...rest } = options
  const headers: Record<string, string> = {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(rest.headers as Record<string, string> ?? {}),
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    credentials: 'include',
    headers,
    body: json ? JSON.stringify(json) : rest.body,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, json?: unknown) => request<T>(path, { method: 'POST', json }),
  put: <T>(path: string, json?: unknown) => request<T>(path, { method: 'PUT', json }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

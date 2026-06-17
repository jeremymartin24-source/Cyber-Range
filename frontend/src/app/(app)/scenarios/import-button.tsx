'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

export default function ScenarioImport() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [yamlPath, setYamlPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleImport() {
    if (!yamlPath.trim()) return
    setLoading(true)
    setError('')
    try {
      await api.post('/api/v1/scenarios/import', { yaml_path: yamlPath.trim() })
      setOpen(false)
      setYamlPath('')
      router.refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
      >
        Import YAML
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-sm rounded-xl border border-gray-700 bg-gray-900 p-6 shadow-xl">
            <h3 className="text-base font-semibold text-gray-100 mb-4">Import Scenario</h3>
            {error && (
              <div className="mb-3 rounded border border-red-800 bg-red-900/30 px-3 py-2 text-xs text-red-300">
                {error}
              </div>
            )}
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">YAML filename</label>
                <input
                  value={yamlPath}
                  onChange={e => setYamlPath(e.target.value)}
                  placeholder="bmg_phishing_campaign.yaml"
                  className="w-full rounded-md bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none font-mono"
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={handleImport}
                  disabled={loading || !yamlPath.trim()}
                  className="flex-1 rounded-md bg-blue-600 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Importing…' : 'Import'}
                </button>
                <button
                  onClick={() => { setOpen(false); setError('') }}
                  className="flex-1 rounded-md border border-gray-700 py-2 text-sm text-gray-400 hover:text-gray-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

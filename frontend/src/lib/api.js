export const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api').replace(/\/+$/, '')
let csrfToken = null
let csrfPending = null

async function getCsrfToken() {
  if (csrfToken) return csrfToken
  if (!csrfPending) {
    csrfPending = fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' })
      .then(async response => {
        const data = await response.json().catch(() => ({}))
        if (!response.ok || !data.csrf_token) throw new Error(data.error || 'Could not initialize the secure session.')
        csrfToken = data.csrf_token
        return csrfToken
      })
      .finally(() => { csrfPending = null })
  }
  return csrfPending
}

export async function api(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers }
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && !path.endsWith('/auth/csrf')) {
    headers['X-CSRF-Token'] = await getCsrfToken()
  }
  const response = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (response.status === 403 && data.code === 'csrf_failed' && headers['X-CSRF-Token']) {
    csrfToken = null
    headers['X-CSRF-Token'] = await getCsrfToken()
    const retry = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...options, headers })
    const retryData = await retry.json().catch(() => ({}))
    if (!retry.ok) {
      if (retry.status === 401) window.dispatchEvent(new CustomEvent('dashboard:session-expired'))
      throw new Error(retryData.error || `Request failed (${retry.status})`)
    }
    if (path.endsWith('/auth/logout')) csrfToken = null
    return retryData
  }
  if (!response.ok) {
    if (response.status === 401 && !path.endsWith('/auth/login') && !path.endsWith('/auth/register')) {
      window.dispatchEvent(new CustomEvent('dashboard:session-expired'))
    }
    throw new Error(data.error || `Request failed (${response.status})`)
  }
  if (path.endsWith('/auth/logout')) csrfToken = null
  return data
}

export async function loadDataset(dataset, onProgress, { signal } = {}) {
  const first = await api(`/data/explorer?dataset=${encodeURIComponent(dataset)}&limit=500&offset=0`, { signal })
  const firstTotal = Number(first.total_rows ?? first.pagination?.total)
  if (!Array.isArray(first.columns) || !Array.isArray(first.rows) || !Number.isFinite(firstTotal) || firstTotal < 0) {
    throw new Error('The data explorer API returned an invalid dataset response. Check that the backend is running the current API version.')
  }
  const rows = [...first.rows]
  const total = Math.min(firstTotal, 100000)
  const offsets = []
  for (let offset = 500; offset < total; offset += 500) offsets.push(offset)
  for (let i = 0; i < offsets.length; i += 5) {
    const batch = await Promise.all(offsets.slice(i, i + 5).map(offset => api(`/data/explorer?dataset=${encodeURIComponent(dataset)}&limit=500&offset=${offset}`, { signal })))
    batch.forEach((page, batchIndex) => {
      if (!Array.isArray(page.rows) || !Array.isArray(page.columns) || page.dataset !== dataset || page.offset !== offsets[i + batchIndex]) {
        throw new Error('The data explorer API returned an inconsistent page. Retry the request or check the backend version.')
      }
      rows.push(...page.rows)
    })
    onProgress?.(Math.min(rows.length, total), total)
  }
  return { ...first, rows, total_rows: total, truncated: firstTotal > total }
}

export const formatNumber = value => value == null || !Number.isFinite(Number(value))
  ? '—'
  : Number(value).toLocaleString('en-IN')

export const compactNumber = value => value == null || !Number.isFinite(Number(value))
  ? '—'
  : Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value))

export const formatDate = value => value
  ? new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
  : 'Date not available'

export function downloadCsv(rows, columns, filename) {
  if (!rows?.length || !columns?.length) return false
  const csv = [columns, ...rows.map(row => columns.map(column => row[column] ?? ''))]
    .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.position = 'fixed'
  link.style.left = '-10000px'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  return true
}

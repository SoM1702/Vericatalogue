import type { BatchResult, EnrichmentResult, ProductRecord, ReviewAgentPlan } from './types'

// Development requests use Vite's same-origin `/api` proxy by default. This
// avoids a fragile CORS dependency when Vite chooses a fallback local port.
// A deployment may still provide a full API origin through VITE_API_BASE_URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function getError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    return body.detail ?? 'The request could not be completed.'
  } catch {
    return 'The request could not be completed.'
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, init)
  if (!response.ok) throw new Error(await getError(response))
  return response.json() as Promise<T>
}

export interface AiStatus {
  enabled: boolean
  configured: boolean
  model: string | null
  mode: 'grounded_candidate_mapping' | 'deterministic_only'
  message: string
}

export function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/api/ai/status')
}

export async function fetchDemoFile(filename: string): Promise<File> {
  const response = await fetch(`${API_BASE}/api/demo-files/${filename}`, { cache: 'no-store' })
  if (!response.ok) throw new Error(await getError(response))
  const blob = await response.blob()
  return new File([blob], filename, { type: blob.type || 'application/octet-stream' })
}

export async function enrichProduct(files: File[], manualTitle: string, manualMpn: string, recordIndex = 0): Promise<EnrichmentResult> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  if (manualTitle.trim()) form.append('manual_title', manualTitle.trim())
  if (manualMpn.trim()) form.append('manual_mpn', manualMpn.trim())
  form.append('record_index', String(recordIndex))
  return request<EnrichmentResult>('/api/enrich', { method: 'POST', body: form })
}

export async function processBatch(file: File): Promise<BatchResult> {
  const form = new FormData()
  form.append('file', file)
  return request<BatchResult>('/api/batch', { method: 'POST', body: form })
}

export async function reviewAttribute(
  productId: string,
  field: string,
  action: 'approve' | 'reject' | 'edit',
  note?: string,
  value?: string,
): Promise<ProductRecord> {
  return request<ProductRecord>(`/api/products/${productId}/attributes/${field}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, note: note || null, value: value || null }),
  })
}

export function getLatestReviewAgentPlan(productId: string): Promise<ReviewAgentPlan> {
  return request<ReviewAgentPlan>(`/api/products/${productId}/review-agent/latest`)
}

export function runReviewAgent(productId: string): Promise<ReviewAgentPlan> {
  return request<ReviewAgentPlan>(`/api/products/${productId}/review-agent/plan`, { method: 'POST' })
}

export function exportUrl(productId: string, format: 'json' | 'csv'): string {
  return `${API_BASE}/api/products/${productId}/export?format=${format}`
}

export function reviewQueueExportUrl(): string {
  return `${API_BASE}/api/review-queue/export`
}

import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'

export interface OcrLine {
  text: string
  confidence: number
  box: number[][]
}

export interface OcrPage {
  page: number
  width: number
  height: number
  lines: OcrLine[]
  text: string
}

export interface DocClassification {
  doc_type: string | null
  confidence: number
  scores: Record<string, number>
}

export interface OcrResult {
  engine: string
  lang: string
  page_count: number
  pages: OcrPage[]
  text: string
  processing_ms: number
  cached: boolean
  classification: DocClassification | null
}

export interface ClassifyResult {
  doc_type: string | null
  confidence: number
  scores: Record<string, number>
  lang: string
  page_count: number
  text_excerpt: string
}

export type OcrJobStatus = 'pending' | 'processing' | 'done' | 'error'

/** Job metadata as returned by the list endpoint (no `result`). */
export interface OcrJobSummary {
  id: string
  status: OcrJobStatus
  original_filename: string | null
  content_type: string | null
  size_bytes: number
  lang: string
  page_count: number | null
  processing_ms: number | null
  doc_type: string | null
  callback_url: string | null
  callback_status: string | null
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

/** Full job as returned by the detail endpoint. */
export interface OcrJob extends OcrJobSummary {
  result: OcrResult | null
}

export interface OcrJobList {
  data: OcrJobSummary[]
  total: number
  page: number
  per_page: number
}

export interface OcrStats {
  pending: number
  processing: number
  done: number
  error: number
  oldest_pending_age_seconds: number | null
  processing_ms_avg: number | null
  processing_ms_p95: number | null
  by_doc_type: Record<string, number>
}

function buildForm(file: File, lang?: string, callbackUrl?: string): FormData {
  const form = new FormData()
  form.append('file', file)
  if (lang) form.append('lang', lang)
  if (callbackUrl) form.append('callback_url', callbackUrl)
  return form
}

export const ocrApi = {
  async scan(file: File, lang?: string): Promise<OcrResult> {
    const { data } = await axios.post(endpoints.ocr.scan, buildForm(file, lang), {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async classify(file: File, lang?: string): Promise<ClassifyResult> {
    const { data } = await axios.post(endpoints.ocr.classify, buildForm(file, lang), {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async createJob(file: File, lang?: string, callbackUrl?: string): Promise<OcrJob> {
    const { data } = await axios.post(
      endpoints.ocr.jobs,
      buildForm(file, lang, callbackUrl),
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },

  async listJobs(params?: {
    page?: number
    per_page?: number
    status?: string
    doc_type?: string
    search?: string
  }): Promise<OcrJobList> {
    const clean = Object.fromEntries(
      Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== ''),
    )
    const { data } = await axios.get(endpoints.ocr.jobs, { params: clean })
    return data
  },

  async getJob(id: string): Promise<OcrJob> {
    const { data } = await axios.get(endpoints.ocr.jobDetail(id))
    return data
  },

  async stats(): Promise<OcrStats> {
    const { data } = await axios.get(endpoints.ocr.stats)
    return data
  },
}

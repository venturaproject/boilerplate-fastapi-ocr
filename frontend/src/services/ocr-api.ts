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

export interface OcrResult {
  engine: string
  lang: string
  page_count: number
  pages: OcrPage[]
  text: string
  processing_ms: number
}

export type OcrJobStatus = 'pending' | 'processing' | 'done' | 'error'

export interface OcrJob {
  id: string
  status: OcrJobStatus
  original_filename: string | null
  content_type: string | null
  size_bytes: number
  lang: string
  page_count: number | null
  callback_url: string | null
  callback_status: string | null
  error: string | null
  result: OcrResult | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface OcrJobList {
  data: OcrJob[]
  total: number
  page: number
  per_page: number
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

  async createJob(file: File, lang?: string, callbackUrl?: string): Promise<OcrJob> {
    const { data } = await axios.post(
      endpoints.ocr.jobs,
      buildForm(file, lang, callbackUrl),
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return data
  },

  async listJobs(params?: { page?: number; per_page?: number }): Promise<OcrJobList> {
    const { data } = await axios.get(endpoints.ocr.jobs, { params })
    return data
  },

  async getJob(id: string): Promise<OcrJob> {
    const { data } = await axios.get(endpoints.ocr.jobDetail(id))
    return data
  },
}

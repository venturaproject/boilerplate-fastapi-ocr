import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'

export type DocumentMode = 'sync' | 'async' | 'classify'
export type DocumentStatus = 'pending' | 'done' | 'error'

export interface DocumentRow {
  id: string
  api_client_id: string | null
  created_by_user_id: string | null
  ocr_job_id: string | null
  mode: DocumentMode
  status: DocumentStatus
  original_filename: string | null
  content_type: string | null
  size_bytes: number
  lang: string
  page_count: number | null
  processing_ms: number | null
  doc_type: string | null
  doc_type_confidence: number | null
  char_count: number | null
  text_excerpt: string | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface DocumentList {
  data: DocumentRow[]
  current_page: number
  last_page: number
  per_page: number
  total: number
}

export interface DocumentStats {
  total: number
  last_24h: number
  by_mode: Record<string, number>
  by_status: Record<string, number>
  by_doc_type: Record<string, number>
  processing_ms_avg: number | null
  processing_ms_p95: number | null
}

export interface DocumentFilters {
  page?: number
  per_page?: number
  search?: string
  mode?: string
  doc_type?: string
  status?: string
}

export const documentsApi = {
  async list(filters: DocumentFilters = {}): Promise<DocumentList> {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== undefined && v !== ''),
    )
    const { data } = await axios.get(endpoints.documents.list, { params })
    return data
  },

  async detail(id: string): Promise<DocumentRow> {
    const { data } = await axios.get(endpoints.documents.detail(id))
    return data
  },

  async stats(): Promise<DocumentStats> {
    const { data } = await axios.get(endpoints.documents.stats)
    return data
  },

  async remove(id: string): Promise<void> {
    await axios.delete(endpoints.documents.detail(id))
  },
}

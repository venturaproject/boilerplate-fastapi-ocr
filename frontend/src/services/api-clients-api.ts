import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'

export interface ApiClientRecord {
  id: string
  name: string
  client_id: string
  scopes: string[]
  active: boolean
  rate_limit: string | null
  monthly_page_quota: number | null
  // "none" | "rules" | "llm" — pins this client's OCR_EXTRACTOR regardless of the global
  // setting; null inherits it. See README § Quotas, metering and secret rotation.
  ocr_extractor_override: string | null
  last_used_at: string | null
  created_at: string
}

export interface UpdateApiClientPayload {
  rate_limit?: string | null
  monthly_page_quota?: number | null
  ocr_extractor_override?: string | null
}

export const OCR_EXTRACTOR_OVERRIDE_OPTIONS = [
  { value: '',      label: 'Heredar del servidor' },
  { value: 'none',  label: 'none — sin extracción de campos' },
  { value: 'rules', label: 'rules — reglas locales (sin salida a terceros)' },
  { value: 'llm',   label: 'llm — proveedor LLM externo' },
]

export interface ApiClientUsage {
  period: string
  pages: number
  requests: number
  monthly_page_quota: number | null
  quota_remaining: number | null
  rate_limit: string | null
}

export interface CreateApiClientPayload {
  name: string
  scopes: string[]
}

export interface CreateApiClientResponse {
  client: ApiClientRecord
  secret: string
}

export const AVAILABLE_SCOPES = [
  { value: 'ocr:write', label: 'OCR — enviar documentos' },
  { value: 'ocr:read',  label: 'OCR — consultar resultados' },
  { value: '*',         label: 'Acceso completo (*)' },
]

export const apiClientsApi = {
  async list(): Promise<ApiClientRecord[]> {
    const { data } = await axios.get(endpoints.apiClients.list)
    return data
  },

  async create(payload: CreateApiClientPayload): Promise<CreateApiClientResponse> {
    const { data } = await axios.post(endpoints.apiClients.create, payload)
    return data
  },

  async update(id: string, payload: UpdateApiClientPayload): Promise<ApiClientRecord> {
    const { data } = await axios.patch(endpoints.apiClients.update(id), payload)
    return data
  },

  async usage(id: string): Promise<ApiClientUsage> {
    const { data } = await axios.get(endpoints.apiClients.usage(id))
    return data
  },

  async rotate(id: string): Promise<CreateApiClientResponse> {
    const { data } = await axios.post(endpoints.apiClients.rotate(id))
    return data
  },

  async revoke(id: string): Promise<void> {
    await axios.delete(endpoints.apiClients.revoke(id))
  },
}

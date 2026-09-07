import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'

export interface ApiClientRecord {
  id: string
  name: string
  client_id: string
  scopes: string[]
  active: boolean
  last_used_at: string | null
  created_at: string
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

  async revoke(id: string): Promise<void> {
    await axios.delete(endpoints.apiClients.revoke(id))
  },
}

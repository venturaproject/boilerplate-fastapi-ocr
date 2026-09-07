import { axios } from '@/lib/axios'
import { API_ENDPOINTS } from '@/config'
import { endpoints } from '@/lib/endpoints'
import { normalizeCollectionPayload, normalizeEntityPayload } from '@/lib/api-utils'

export type DispositivoMutationPayload = object

export const dispositivosApi = {
  async list(params?: Record<string, string>) {
    const { data } = await axios.get(API_ENDPOINTS.dispositivos, { params })
    return data
  },

  async detail(id: string | number) {
    const { data } = await axios.get(`${API_ENDPOINTS.dispositivos}/${id}`)
    return normalizeEntityPayload<Record<string, unknown>>(data)
  },

  async brands() {
    const { data } = await axios.get(`${API_ENDPOINTS.dispositivos}/marcas`)
    return normalizeCollectionPayload<{ id?: number; nombre: string }>(data)
  },

  async modelOptions(brand: string) {
    const { data } = await axios.get(endpoints.deviceModels.byBrand(brand))
    return (data && typeof data === 'object' ? data : {}) as Record<string, string>
  },

  async create(payload: DispositivoMutationPayload) {
    const { data } = await axios.post(API_ENDPOINTS.dispositivos, payload)
    return data
  },

  async update(id: string | number, payload: DispositivoMutationPayload) {
    const { data } = await axios.put(`${API_ENDPOINTS.dispositivos}/${id}`, payload)
    return data
  },

  async deliver(id: string | number, payload: Record<string, unknown>) {
    const { data } = await axios.post(endpoints.dispositivos.deliver(id), payload)
    return data
  },
}

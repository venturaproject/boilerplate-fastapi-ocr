import { axios } from '@/lib/axios'
import { API_ENDPOINTS } from '@/config'
import { normalizeEntityPayload } from '@/lib/api-utils'

export const trabajadoresApi = {
  async list(params?: Record<string, string>) {
    const { data } = await axios.get(API_ENDPOINTS.trabajadores, { params })
    return data
  },

  async detail(id: string | number) {
    const { data } = await axios.get(`${API_ENDPOINTS.trabajadores}/${id}`)
    return normalizeEntityPayload<Record<string, unknown>>(data)
  },
}

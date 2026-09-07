import { axios } from '@/lib/axios'
import { API_ENDPOINTS } from '@/config'
import { endpoints } from '@/lib/endpoints'
import { normalizeCollectionPayload, normalizeEntityPayload } from '@/lib/api-utils'

export type TelefonoMutationPayload = object

export const telefonosApi = {
  async list(params?: Record<string, string>) {
    const { data } = await axios.get(API_ENDPOINTS.telefonos, { params })
    return data
  },

  async detail(id: string | number) {
    const { data } = await axios.get(`${API_ENDPOINTS.telefonos}/${id}`)
    return normalizeEntityPayload<Record<string, unknown>>(data)
  },

  async tipologias() {
    const { data } = await axios.get(`${API_ENDPOINTS.telefonos}/tipologias`)
    return normalizeCollectionPayload<{ id: number; nombre: string }>(data)
  },

  async estados() {
    const { data } = await axios.get(`${API_ENDPOINTS.telefonos}/estados`)
    return normalizeCollectionPayload<{ id: number; nombre: string }>(data)
  },

  async update(id: string | number, payload: TelefonoMutationPayload) {
    const { data } = await axios.put(`${API_ENDPOINTS.telefonos}/${id}`, payload)
    return data
  },

  async desactivar(id: string | number) {
    const { data } = await axios.post(endpoints.telefonos.desactivar(id), {})
    return data
  },

  async sync() {
    const { data } = await axios.post('/api/v1/telefonos/sync', {})
    return data
  },

  async bulkDesactivar(payload: { ids?: number[]; select_all?: number; filters?: Record<string, unknown> }) {
    const { data } = await axios.post('/api/v1/telefonos/bulk-desactivar', payload)
    return data
  },

  async createActuacion(phoneId: string | number, payload: { nombre: string }) {
    const { data } = await axios.post(endpoints.telefonos.actions.store(phoneId), payload)
    return data
  },

  async updateActuacion(actionId: string | number, payload: { nombre: string }) {
    const { data } = await axios.put(endpoints.telefonos.actions.detail(actionId), payload)
    return data
  },

  async deleteActuacion(actionId: string | number) {
    await axios.delete(endpoints.telefonos.actions.detail(actionId))
  },
}

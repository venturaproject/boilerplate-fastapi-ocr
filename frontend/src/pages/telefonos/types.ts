export interface PhoneStatus {
  id: number
  nombre: string
}

export interface TelefonoTrabajador {
  id: number
  nombre_completo: string
  telefono_synergy: string | null
}

export interface Telefono {
  id: number
  telefono: string
  plan: string
  nplan: string
  tipo: string
  pin: string | null
  puk: string | null
  estado_telefonos_id: number
  tipologias_id: number | null
  notas: string | null
  status: PhoneStatus | null
  trabajador: TelefonoTrabajador | null
}

export interface TelefonoStats {
  total: number
  activos: number
  congelados: number
  bajas: number
  sinDatos: number
}

export interface TelefonoFilters {
  search?: string
  status?: string
  plan?: string
  [key: string]: string | undefined
}

export interface PhoneFilterOptions {
  planes: string[]
}

export const STATUS_BADGE_CLASS: Record<number, string> = {
  1: 'rounded-full border bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-50',
  2: 'rounded-full border bg-sky-50 text-sky-700 border-sky-200 hover:bg-sky-50',
  3: 'rounded-full border bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-100',
  5: 'rounded-full border bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-50',
}

export function statusBadgeClass(statusId: number): string {
  return (
    STATUS_BADGE_CLASS[statusId] ??
    'rounded-full border bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-100'
  )
}

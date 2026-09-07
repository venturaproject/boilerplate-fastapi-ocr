export interface Trabajador {
  id: number
  synergy_res_id: number
  nombre_completo: string
  email: string | null
  ubicacion: string | null
  ciudad: string | null
  loc: string | null
  telefono_synergy: string | null
  imei: string | null
  telefonos_id: number | null
  emp_stat: string | null
  activo: boolean
  fecha_alta: string | null
  fecha_baja: string | null
}

export interface TrabajadorStats {
  activos: number
  conTelefono: number
  incorporadosEsteMes: number
  conImei: number
}

export interface TrabajadorFilters {
  search?: string
  activo?: string
  ubicacion?: string
  ciudad?: string
  date_from?: string
  date_to?: string
  [key: string]: string | undefined
}

export interface FilterOptions {
  ubicaciones: string[]
  ciudades: string[]
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

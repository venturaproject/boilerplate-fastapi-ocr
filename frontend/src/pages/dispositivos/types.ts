export interface DeviceEmployee {
  id: number
  nombre_completo: string
  email: string | null
}

export interface Dispositivo {
  id: number
  marca: string | null
  modelo: string | null
  imei: string | null
  numero: string | null
  grupo: string | null
  otros: string | null
  employee_synergy_res_id: number | null
  employee: DeviceEmployee | null
}

export interface DeliveryReceipt {
  id: number
  device_id: number
  employee_synergy_res_id: number | null
  user_id: number | null
  signature_path: string | null
  pdf_path: string | null
  email_sent_to: string | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
  employee?: { nombre_completo: string; email: string | null } | null
  user?: { name: string } | null
}

export interface DispositivoStats {
  total: number
  withImei: number
  withNumero: number
  assigned: number
  unassigned: number
}

export interface DispositivoFilters {
  search?: string
  marca?: string
  tipo?: string
  grupo?: string
  [key: string]: string | undefined
}

export interface DeviceFilterOptions {
  marcas: string[]
  tipos: string[]
}

export type BrandOptions = Record<string, string>
export type ModelOptions = Record<string, string>
export type TypeOptions = Record<string, string>

export interface TrabajadorOption {
  synergy_res_id: number
  nombre_completo: string
}

export interface AssociatedPhone {
  id: number
  telefono: string
  estado_telefonos_id: number
  status_nombre: string
  nplan: string
  trabajador_nombre: string | null
  activo: boolean
  fecha_cese: string | null
}

export interface AssociatedEmployee {
  id: number
  nombre_completo: string
  email: string | null
  ubicacion: string | null
  telefono: string | null
  telefono_synergy: string | null
  activo: boolean
  fecha_cese: string | null
}

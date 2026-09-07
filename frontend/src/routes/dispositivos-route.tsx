import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useParams, useLocation } from 'react-router-dom'
import DispositivosPage from '@/pages/dispositivos'
import DispositivoShow from '@/pages/dispositivos/show'
import DispositivoEdit from '@/pages/dispositivos/edit'
import DispositivoCreate from '@/pages/dispositivos/create'
import { RoutePending } from '@/components/route-pending'
import NotFoundError from '@/pages/errors/not-found-error'
import { normalizePaginatedPayload } from '@/lib/api-utils'
import { dispositivosApi } from '@/services/dispositivos-api'
import { telefonosApi } from '@/services/telefonos-api'
import { trabajadoresApi } from '@/services/trabajadores-api'

export default function DispositivosRoute() {
  const [searchParams] = useSearchParams()
  const { id } = useParams()
  const location = useLocation()
  const filters = Object.fromEntries(searchParams.entries())

  const isCreate = location.pathname.endsWith('/create')
  const isEdit = !!id && location.pathname.endsWith('/edit')
  const isShow = !!id && !isEdit

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['dispositivos', filters],
    queryFn: () => dispositivosApi.list(filters),
    enabled: !isCreate && !isEdit && !isShow,
  })

  const { data: rawDeviceData, isLoading: deviceLoading, isError: deviceError } = useQuery({
    queryKey: ['dispositivos', id],
    queryFn: () => dispositivosApi.detail(String(id)),
    enabled: !!id,
  })

  const { data: brandsData } = useQuery({
    queryKey: ['dispositivos-marcas'],
    queryFn: () => dispositivosApi.brands(),
    enabled: isCreate || isEdit,
  })

  const { data: trabajadoresData } = useQuery({
    queryKey: ['trabajadores-all'],
    queryFn: () => trabajadoresApi.list({ per_page: '1000' }),
    enabled: isCreate || isEdit,
  })

  const { data: telefonosData } = useQuery({
    queryKey: ['telefonos-all'],
    queryFn: () => telefonosApi.list({ per_page: '1000' }),
    enabled: isCreate || isEdit,
  })

  const brandOptions: Record<string, string> = Object.fromEntries(
    (brandsData ?? []).map((b) => [b.nombre, b.nombre])
  )

  const typeOptions: Record<string, string> = {
    'Teléfonos': 'Teléfonos',
    'Tabletas': 'Tabletas',
    'Bases Wifi': 'Bases Wifi',
    'Portátiles': 'Portátiles',
    'Otros': 'Otros',
  }

  const trabajadorOptions = (trabajadoresData?.results ?? []).map(
    (t: { synergy_res_id: number; nombre_completo: string }) => ({
      synergy_res_id: t.synergy_res_id,
      nombre_completo: t.nombre_completo,
    })
  )

  const phoneOptions = (telefonosData?.results ?? []).map(
    (t: { id: number; numero: string }) => ({ id: t.id, telefono: t.numero })
  )

  const deviceData = rawDeviceData

  if (isEdit) {
    if (deviceLoading) return <RoutePending />
    if (deviceError || !deviceData) return <NotFoundError />
    return (
      <DispositivoEdit
        device={deviceData as any}
        selectedBrand={(deviceData as any)?.marca ?? null}
        selectedGrupo={(deviceData as any)?.grupo ?? null}
        brandOptions={brandOptions}
        typeOptions={typeOptions}
        trabajadorOptions={trabajadorOptions}
        phoneOptions={phoneOptions}
      />
    )
  }

  if (isCreate) {
    return (
      <DispositivoCreate
        brandOptions={brandOptions}
        typeOptions={typeOptions}
        trabajadorOptions={trabajadorOptions}
        phoneOptions={phoneOptions}
      />
    )
  }

  if (isShow) {
    if (deviceLoading) return <RoutePending />
    if (deviceError || !deviceData) return <NotFoundError />
    return (
      <DispositivoShow
        device={deviceData as any}
        deliveryReceipts={[]}
        associatedPhones={[]}
        associatedEmployees={[]}
      />
    )
  }

  if (listLoading) return <RoutePending />

  const dispositivos = listData
    ? normalizePaginatedPayload<any>(listData)
    : { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 }

  const filterOptions = {
    marcas: (listData?.marcas ?? []).map((m: { nombre: string }) => m.nombre),
    tipos: [...new Set<string>((listData?.results ?? []).map((d: { grupo?: string }) => d.grupo).filter(Boolean))].sort(),
  }

  return (
    <DispositivosPage
      dispositivos={dispositivos}
      filters={filters}
      filterOptions={filterOptions}
    />
  )
}

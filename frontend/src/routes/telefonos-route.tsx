import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useParams, useLocation } from 'react-router-dom'
import TelefonosPage from '@/pages/telefonos'
import ShowPhone from '@/pages/telefonos/show'
import EditPhone from '@/pages/telefonos/edit'
import { RoutePending } from '@/components/route-pending'
import NotFoundError from '@/pages/errors/not-found-error'
import { normalizePaginatedPayload } from '@/lib/api-utils'
import { telefonosApi } from '@/services/telefonos-api'

export default function TelefonosRoute() {
  const [searchParams] = useSearchParams()
  const { id } = useParams()
  const location = useLocation()
  const filters = Object.fromEntries(searchParams.entries())

  const isEdit = !!id && location.pathname.endsWith('/edit')
  const isShow = !!id && !isEdit

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['telefonos', filters],
    queryFn: () => telefonosApi.list(filters),
    enabled: !isEdit && !isShow,
  })

  const { data: rawPhoneData, isLoading: phoneLoading, isError: phoneError } = useQuery({
    queryKey: ['telefonos', id],
    queryFn: () => telefonosApi.detail(String(id)),
    enabled: !!id,
  })

  const { data: tipologiasData = [] } = useQuery({
    queryKey: ['tipologias'],
    queryFn: () => telefonosApi.tipologias(),
    enabled: isEdit,
  })

  const { data: estadosData = [] } = useQuery({
    queryKey: ['telefonos-estados'],
    queryFn: () => telefonosApi.estados(),
    enabled: isEdit,
  })

  const tipologiaOptions: Record<number, string> = Object.fromEntries(
    tipologiasData.map((t) => [t.id, t.nombre])
  )

  const phoneData = rawPhoneData as any
  const actuaciones = Array.isArray(phoneData?.actuaciones) ? phoneData.actuaciones : []

  if (isEdit) {
    if (phoneLoading) return <RoutePending />
    if (phoneError || !phoneData) return <NotFoundError />
    return (
      <EditPhone
        phone={phoneData as any}
        statuses={estadosData as any}
        tipologiaOptions={tipologiaOptions}
        history={[]}
        actions={actuaciones as any}
      />
    )
  }

  if (isShow) {
    if (phoneLoading) return <RoutePending />
    if (phoneError || !phoneData) return <NotFoundError />
    return (
      <ShowPhone
        phone={phoneData as any}
        history={[]}
        actions={actuaciones as any}
      />
    )
  }

  if (listLoading) return <RoutePending />

  const telefonos = listData
    ? normalizePaginatedPayload<any>(listData)
    : { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 }

  return (
    <TelefonosPage
      telefonos={telefonos}
      filters={filters}
      estados={listData?.estados ?? []}
      stats={listData?.stats ?? { total: 0, activos: 0 }}
    />
  )
}

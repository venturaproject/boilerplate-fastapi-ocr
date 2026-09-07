import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useParams, useLocation } from 'react-router-dom'
import TrabajadoresPage from '@/pages/trabajadores'
import TrabajadorShow from '@/pages/trabajadores/show'
import { RoutePending } from '@/components/route-pending'
import NotFoundError from '@/pages/errors/not-found-error'
import { normalizePaginatedPayload } from '@/lib/api-utils'
import { trabajadoresApi } from '@/services/trabajadores-api'

export default function TrabajadoresRoute() {
  const [searchParams] = useSearchParams()
  const { id } = useParams()
  const location = useLocation()
  const filters = Object.fromEntries(searchParams.entries())

  const isShow = !!id

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['trabajadores', filters],
    queryFn: () => trabajadoresApi.list(filters),
    enabled: !isShow,
  })

  const { data: rawTrabajadorData, isLoading: trabajadorLoading, isError: trabajadorError } = useQuery({
    queryKey: ['trabajadores', id],
    queryFn: () => trabajadoresApi.detail(String(id)),
    enabled: !!id,
  })

  const trabajadorData = rawTrabajadorData

  if (isShow) {
    if (trabajadorLoading) return <RoutePending />
    if (trabajadorError || !trabajadorData) return <NotFoundError />
    return <TrabajadorShow trabajador={trabajadorData as any} />
  }

  if (listLoading) return <RoutePending />

  const trabajadores = listData
    ? normalizePaginatedPayload<any>(listData)
    : { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 }

  return (
    <TrabajadoresPage
      trabajadores={trabajadores}
      filters={filters}
    />
  )
}

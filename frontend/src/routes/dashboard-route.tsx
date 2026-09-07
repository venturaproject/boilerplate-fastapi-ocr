import { useQuery } from '@tanstack/react-query'
import { axios } from '@/lib/axios'
import { API_ENDPOINTS } from '@/config'
import Dashboard from '@/pages/dashboard/index'

const EMPTY_DOC_STATS = {
  total: 0,
  last_24h: 0,
  by_mode: {},
  by_status: {},
  by_doc_type: {},
  processing_ms_avg: null,
  processing_ms_p95: null,
}

const EMPTY_JOB_STATS = {
  pending: 0,
  processing: 0,
  done: 0,
  error: 0,
  oldest_pending_age_seconds: null,
  processing_ms_avg: null,
  processing_ms_p95: null,
  by_doc_type: {},
}

export default function DashboardRoute() {
  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => axios.get(API_ENDPOINTS.dashboard).then((r) => r.data),
    refetchInterval: 15000,
  })

  return (
    <Dashboard
      documents={data?.documents ?? EMPTY_DOC_STATS}
      jobs={data?.jobs ?? EMPTY_JOB_STATS}
      recent={data?.recent ?? []}
    />
  )
}

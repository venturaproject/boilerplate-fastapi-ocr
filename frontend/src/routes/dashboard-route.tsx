import { useQuery } from '@tanstack/react-query'
import { axios } from '@/lib/axios'
import { API_ENDPOINTS } from '@/config'
import Dashboard from '@/pages/dashboard/index'

const DEFAULT_STATS = { activos: 0, conTelefono: 0, incorporadosEsteMes: 0, conImei: 0 }
const DEFAULT_PHONE = { total: 0, activos: 0, congelados: 0, bajas: 0, sinDatos: 0 }

export default function DashboardRoute() {
  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => axios.get(API_ENDPOINTS.dashboard).then((r) => r.data),
  })

  return (
    <Dashboard
      stats={data?.stats ?? DEFAULT_STATS}
      phoneStats={data?.phoneStats ?? DEFAULT_PHONE}
      recentDevices={data?.recentDevices ?? []}
      monthlyWorkerStats={data?.monthlyWorkerStats ?? []}
    />
  )
}
import {AuthenticatedLayout} from "@/layouts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {Tabs, TabsContent, TabsList, TabsTrigger} from '@/components/ui/tabs'
import {Main} from '@/components/layout/main'
import { MetricStatCard } from '@/components/metric-stat-card'
import {PageProps} from '@/types'
import {useI18n} from '@/i18n/context'
import { Overview } from './overview'
import { PhoneStatusChart } from './phone-status-chart'
import { RecentDevices } from './recent-devices'
import { BarChartExample } from './analytics/BarChartExample'
import { LineChartExample } from './analytics/LineChartExample'
import {AreaChartDemo} from "./reports/AreaChartDemo"
import {BarChartMultiple} from "./reports/BarChartMultiple"
import {RadialChartShape} from "./reports/RadialChartShape"
import {BarChartHorizontal} from "./reports/BarChartHorizontal"
import {BarChartSingle} from "./reports/BarChartSingle"
import {LineChartMultiple} from "./reports/LineChartMultiple"
import {BarChartActive} from "./reports/BarChartActive"
import {PieChartDemo} from "./reports/PieChartDemo"
import {PieChartDonut} from "./reports/PieChartDonut"
import {PieChartInteractive} from "./reports/PieChartInteractive"
import {RadialChartLabel} from "./reports/RadialChartLabel"
import {RadialChartText} from "./reports/RadialChartText";
import NotificationList from '@/components/notification/notification-list';
import { ConsultaAsistidaPanel } from '@/components/consulta-asistida-panel'
import {
  Users,
  UserCheck,
  UserPlus,
  Phone,
} from 'lucide-react'

interface DashboardPageProps extends PageProps {
  stats: {
    activos: number;
    conTelefono: number;
    incorporadosEsteMes: number;
    conImei: number;
  }
  phoneStats: {
    total: number;
    activos: number;
    congelados: number;
    bajas: number;
    sinDatos: number;
  }
  recentDevices: Array<{
    id: number;
    marca: string | null;
    modelo: string | null;
    numero: string | null;
    grupo: string | null;
    employee_nombre: string | null;
    updated_at: string;
  }>
  monthlyWorkerStats: Array<{
    month: string;
    incorporations: number;
  }>
}

const trendSeries = {
  workers: [7, 10, 8, 11, 9, 12, 10, 13],
  hires: [5, 7, 6, 9, 7, 10, 8, 12],
  phone: [4, 6, 5, 8, 6, 9, 7, 11],
  activity: [9, 7, 10, 8, 11, 9, 12, 10],
}

export default function Dashboard({ stats, phoneStats, recentDevices, monthlyWorkerStats }: DashboardPageProps) {
  const { t } = useI18n()

  return (
    <>
      <AuthenticatedLayout title="Dashboard">
        <Main>
          <div className='mb-2 flex items-center justify-between space-y-2'>
            <h1 className='text-2xl font-bold tracking-tight'>Dashboard</h1>
            <div className='flex items-center space-x-2'></div>
          </div>
          <Tabs
            orientation='vertical'
            defaultValue='overview'
            className='space-y-4'
          >
            <div className='w-full overflow-x-auto pb-2'>
              <TabsList>
                <TabsTrigger value='overview'>{t('overview_tab')}</TabsTrigger>
                <TabsTrigger value='analytics'>
                  {t('analytics_tab')}
                </TabsTrigger>
                <TabsTrigger value='reports'>{t('reports_tab')}</TabsTrigger>
                <TabsTrigger value='notifications'>{t('notifications_tab')}</TabsTrigger>
                <TabsTrigger value='ia'>Búsqueda IA</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value='overview' className='space-y-4'>
              <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                <MetricStatCard
                  title="Trabajadores Activos"
                  value={stats.activos}
                  subtitle="En activo actualmente"
                  icon={Users}
                  trend={85}
                  sparklineColor="#10b981"
                  sparklineData={trendSeries.workers}
                />
                <MetricStatCard
                  title="Con Teléfono"
                  value={stats.conTelefono}
                  subtitle="Con teléfono registrado"
                  icon={Phone}
                  trend={100}
                  sparklineColor="#6366f1"
                  sparklineData={trendSeries.phone}
                />
                <MetricStatCard
                  title="Nuevos este Mes"
                  value={stats.incorporadosEsteMes}
                  subtitle="Incorporados este mes"
                  icon={UserPlus}
                  trend={100}
                  sparklineColor="#f59e0b"
                  sparklineData={trendSeries.hires}
                />
                <MetricStatCard
                  title="Con IMEI"
                  value={stats.conImei}
                  subtitle="Con IMEI registrado"
                  icon={UserCheck}
                  trend={90}
                  sparklineColor="#3b82f4"
                  sparklineData={trendSeries.activity}
                />
              </div>
              <div className='grid grid-cols-1 gap-4 lg:grid-cols-2'>
                <Card className='col-span-1'>
                  <CardHeader>
                    <CardTitle>{t('phone_status')}</CardTitle>
                  </CardHeader>
                  <CardContent className='pl-2'>
                    <PhoneStatusChart stats={phoneStats} />
                  </CardContent>
                </Card>
                <Card className='col-span-1'>
                  <CardHeader>
                    <CardTitle>{t('recent_devices')}</CardTitle>
                    <CardDescription>
                      {t('recent_devices_description')}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <RecentDevices devices={recentDevices} />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value='analytics' className='space-y-4'>
              <div className='grid gap-4 lg:grid-cols-2'>
                <BarChartExample stats={phoneStats} />
                <LineChartExample monthlyStats={monthlyWorkerStats} />
              </div>
            </TabsContent>

            <TabsContent value='reports' className='space-y-4'>
              <div className='grid flex-1 scroll-mt-20 items-start gap-10 md:grid-cols-2 md:gap-4 lg:grid-cols-3'>
                <AreaChartDemo />
                <BarChartHorizontal />
                <BarChartMultiple />
                <BarChartSingle />
                <LineChartMultiple />
                <BarChartActive />
                <RadialChartLabel />
                <PieChartInteractive />
                <RadialChartShape />
                <PieChartDonut />
                <PieChartDemo />
                <RadialChartText />
              </div>
            </TabsContent>
            <TabsContent value='notifications' className='space-y-4'>
              <div className='max-w-2xl'>
                <NotificationList />
              </div>
            </TabsContent>
            <TabsContent value='ia' className='space-y-4'>
              <ConsultaAsistidaPanel />
            </TabsContent>
          </Tabs>
        </Main>
      </AuthenticatedLayout>
    </>
  )
}

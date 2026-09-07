import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import { useI18n } from '@/i18n/context'

const COLORS = ['#10b981', '#60a5fa', '#f87171', '#94a3b8']

interface PhoneStatusChartProps {
  stats: {
    activos: number
    congelados: number
    bajas: number
    sinDatos: number
  }
}

export function PhoneStatusChart({ stats }: PhoneStatusChartProps) {
  const { t } = useI18n()

  const data = [
    { name: t('stat_telefonos_activos_title'), value: stats.activos },
    { name: t('stat_telefonos_congelados_title'), value: stats.congelados },
    { name: t('stat_telefonos_bajas_title'), value: stats.bajas },
    { name: t('tab_sin_datos'), value: stats.sinDatos },
  ]

  return (
    <ResponsiveContainer width='100%' height={350}>
      <BarChart data={data}>
        <XAxis
          dataKey='name'
          stroke='#888888'
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke='#888888'
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value}`}
        />
        <Tooltip
          formatter={(value: number) => [value, '']}
          labelStyle={{ color: '#888' }}
        />
        <Bar dataKey='value' radius={[4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

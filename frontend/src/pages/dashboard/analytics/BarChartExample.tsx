"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { useI18n } from "@/i18n/context"

interface PhoneStatusData {
  activos: number
  congelados: number
  bajas: number
  sinDatos: number
}

interface BarChartExampleProps {
  stats: PhoneStatusData
}

const chartConfig = {
  activos: {
    label: "Activos",
    color: "hsl(var(--chart-1))",
  },
  congelados: {
    label: "Congelados",
    color: "hsl(var(--chart-2))",
  },
  bajas: {
    label: "Bajas",
    color: "hsl(var(--chart-3))",
  },
  sinDatos: {
    label: "Sin Datos",
    color: "hsl(var(--chart-4))",
  },
} satisfies ChartConfig

export function BarChartExample({ stats }: BarChartExampleProps) {
  const { t } = useI18n()

  const chartData = [
    {
      status: t('status_active'),
      count: stats.activos,
      fill: "var(--color-activos)",
    },
    {
      status: t('status_frozen'),
      count: stats.congelados,
      fill: "var(--color-congelados)",
    },
    {
      status: t('status_inactive'),
      count: stats.bajas,
      fill: "var(--color-bajas)",
    },
    {
      status: t('status_no_data'),
      count: stats.sinDatos,
      fill: "var(--color-sinDatos)",
    },
  ]

  const total = stats.activos + stats.congelados + stats.bajas + stats.sinDatos

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('phone_status_distribution')}</CardTitle>
        <CardDescription>
          {t('total_phones_count', { count: total })}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart accessibilityLayer data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="status"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Bar
              dataKey="count"
              radius={8}
              fill="var(--color-activos)"
            />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

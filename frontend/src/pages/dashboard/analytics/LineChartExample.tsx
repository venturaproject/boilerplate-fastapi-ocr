"use client"

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

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

interface MonthlyData {
  month: string
  incorporations: number
}

interface LineChartExampleProps {
  monthlyStats: MonthlyData[]
}

const chartConfig = {
  incorporations: {
    label: "Incorporaciones",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig

export function LineChartExample({ monthlyStats }: LineChartExampleProps) {
  const { t } = useI18n()

  const chartData = monthlyStats.map((item) => ({
    month: item.month,
    incorporations: item.incorporations,
  }))

  const total = monthlyStats.reduce((sum, item) => sum + item.incorporations, 0)
  const avg = monthlyStats.length > 0 
    ? Math.round(total / monthlyStats.length) 
    : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('worker_incorporations')}</CardTitle>
        <CardDescription>
          {t('monthly_incorporations_last_6_months', { total })}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <LineChart accessibilityLayer data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value) => value.slice(0, 3)}
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
            <Line
              dataKey="incorporations"
              type="monotone"
              stroke="var(--color-incorporations)"
              strokeWidth={2}
              dot={{ fill: "var(--color-incorporations)", strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

import { AuthenticatedLayout } from '@/layouts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Main } from '@/components/layout/main'
import { MetricStatCard } from '@/components/metric-stat-card'
import NotificationList from '@/components/notification/notification-list'
import { FileText, Clock, Layers, Timer } from 'lucide-react'
import { DOC_TYPE_LABEL } from '@/pages/ocr/index'
import type { DocumentStats } from '@/services/documents-api'
import type { OcrStats } from '@/services/ocr-api'

const MODE_LABEL: Record<string, string> = {
  sync: 'Síncrono',
  async: 'Asíncrono',
  classify: 'Clasificación',
}

interface RecentDocument {
  id: string
  original_filename: string | null
  mode: string
  status: string
  doc_type: string | null
  lang: string
  page_count: number | null
  processing_ms: number | null
  created_at: string
}

interface DashboardPageProps {
  documents: DocumentStats
  jobs: OcrStats
  recent: RecentDocument[]
}

const EMPTY_DOC_STATS: DocumentStats = {
  total: 0,
  last_24h: 0,
  by_mode: {},
  by_status: {},
  by_doc_type: {},
  processing_ms_avg: null,
  processing_ms_p95: null,
}

function breakdown(map: Record<string, number>, label: (k: string) => string) {
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map(([, v]) => v))
  return { entries, max, label }
}

export default function Dashboard({ documents, jobs, recent }: DashboardPageProps) {
  const docs = documents ?? EMPTY_DOC_STATS

  return (
    <AuthenticatedLayout title="Dashboard">
      <Main>
        <div className="mb-2 flex items-center justify-between space-y-2">
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        </div>

        <Tabs orientation="vertical" defaultValue="overview" className="space-y-4">
          <div className="w-full overflow-x-auto pb-2">
            <TabsList>
              <TabsTrigger value="overview">Resumen</TabsTrigger>
              <TabsTrigger value="notifications">Notificaciones</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricStatCard
                title="Documentos"
                value={docs.total}
                subtitle="Procesados por la API"
                icon={FileText}
                sparklineColor="#6366f1"
              />
              <MetricStatCard
                title="Últimas 24 h"
                value={docs.last_24h}
                subtitle="Documentos recientes"
                icon={Clock}
                sparklineColor="#10b981"
              />
              <MetricStatCard
                title="Trabajos en cola"
                value={jobs?.pending ?? 0}
                subtitle={`${jobs?.processing ?? 0} procesando · ${jobs?.error ?? 0} con error`}
                icon={Layers}
                sparklineColor="#f59e0b"
              />
              <MetricStatCard
                title="Latencia media"
                value={
                  docs.processing_ms_avg != null
                    ? `${Math.round(docs.processing_ms_avg)} ms`
                    : '—'
                }
                subtitle={
                  docs.processing_ms_p95 != null
                    ? `p95 ${Math.round(docs.processing_ms_p95)} ms`
                    : 'Sin datos'
                }
                icon={Timer}
                sparklineColor="#3b82f4"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Por tipo de documento</CardTitle>
                  <CardDescription>Clasificación detectada por el OCR</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {Object.keys(docs.by_doc_type).length === 0 && (
                    <p className="text-muted-foreground text-sm">Sin datos todavía.</p>
                  )}
                  {breakdown(docs.by_doc_type, (k) => DOC_TYPE_LABEL[k] ?? k).entries.map(
                    ([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>{DOC_TYPE_LABEL[key] ?? key}</span>
                          <span className="tabular-nums text-muted-foreground">{value}</span>
                        </div>
                        <div className="h-2 rounded bg-muted">
                          <div
                            className="h-2 rounded bg-primary"
                            style={{
                              width: `${(value / breakdown(docs.by_doc_type, (k) => k).max) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Por modo</CardTitle>
                  <CardDescription>Cómo se llamó a la API</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {Object.keys(docs.by_mode).length === 0 && (
                    <p className="text-muted-foreground text-sm">Sin datos todavía.</p>
                  )}
                  {breakdown(docs.by_mode, (k) => MODE_LABEL[k] ?? k).entries.map(([key, value]) => (
                    <div key={key} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>{MODE_LABEL[key] ?? key}</span>
                        <span className="tabular-nums text-muted-foreground">{value}</span>
                      </div>
                      <div className="h-2 rounded bg-muted">
                        <div
                          className="h-2 rounded bg-primary"
                          style={{
                            width: `${(value / breakdown(docs.by_mode, (k) => k).max) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Actividad reciente</CardTitle>
                <CardDescription>Últimos documentos procesados</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Archivo</TableHead>
                        <TableHead>Modo</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Creado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(recent ?? []).map((d) => (
                        <TableRow key={d.id}>
                          <TableCell className="font-medium">
                            {d.original_filename ?? d.id.slice(0, 8)}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{MODE_LABEL[d.mode] ?? d.mode}</Badge>
                          </TableCell>
                          <TableCell>{d.status}</TableCell>
                          <TableCell>
                            {d.doc_type ? (DOC_TYPE_LABEL[d.doc_type] ?? d.doc_type) : '—'}
                          </TableCell>
                          <TableCell className="text-muted-foreground text-xs">
                            {new Date(d.created_at).toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))}
                      {(recent ?? []).length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center text-muted-foreground h-24">
                            Sin documentos todavía
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notifications" className="space-y-4">
            <div className="max-w-2xl">
              <NotificationList />
            </div>
          </TabsContent>
        </Tabs>
      </Main>
    </AuthenticatedLayout>
  )
}

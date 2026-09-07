import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { PaginationFooter } from '@/components/pagination-footer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { CheckCircle2, Clock, Layers, Loader2, RefreshCw, Send, XCircle } from 'lucide-react'
import { ocrApi, type OcrJobStatus, type OcrJobSummary } from '@/services/ocr-api'
import { DOC_TYPE_LABEL } from './index'

const PER_PAGE = 20

const STATUS_VARIANT: Record<OcrJobStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  pending: 'outline',
  processing: 'secondary',
  done: 'default',
  error: 'destructive',
}

function StatusBadge({ status }: { status: OcrJobStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{status}</Badge>
}

export default function OcrJobs() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [lang, setLang] = useState('es')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)

  const jobsQuery = useQuery({
    queryKey: ['ocr-jobs', page],
    queryFn: () => ocrApi.listJobs({ page, per_page: PER_PAGE }),
    refetchInterval: (query) =>
      query.state.data?.data.some((j) => j.status === 'pending' || j.status === 'processing')
        ? 3000
        : false,
  })

  const detailQuery = useQuery({
    queryKey: ['ocr-job', selected],
    queryFn: () => ocrApi.getJob(selected as string),
    enabled: !!selected,
    refetchInterval: (query) =>
      query.state.data && ['pending', 'processing'].includes(query.state.data.status) ? 2000 : false,
  })

  const statsQuery = useQuery({
    queryKey: ['ocr-stats'],
    queryFn: () => ocrApi.stats(),
    refetchInterval: 5000,
  })

  const create = useMutation({
    mutationFn: () => ocrApi.createJob(file as File, lang, callbackUrl || undefined),
    onSuccess: (job) => {
      setFile(null)
      setCallbackUrl('')
      setPage(1)
      setSelected(job.id)
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['ocr-stats'] })
    },
  })

  const list = jobsQuery.data
  const jobs: OcrJobSummary[] = list?.data ?? []
  const stats = statsQuery.data
  const total = list?.total ?? 0
  const lastPage = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <AuthenticatedLayout title="Trabajos OCR">
      <Main>
        <div className="grid flex-1 items-start gap-4 md:gap-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Trabajos OCR (asíncrono)</h2>
            <p className="text-muted-foreground">
              Encola documentos; el worker los procesa en segundo plano. Si indicas un
              <code className="mx-1 rounded bg-muted px-1">callback_url</code>
              recibirás el resultado por webhook.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricStatCard
              title="En cola"
              value={stats?.pending ?? 0}
              subtitle={
                stats?.oldest_pending_age_seconds != null
                  ? `más antiguo hace ${Math.round(stats.oldest_pending_age_seconds)} s`
                  : 'Sin pendientes'
              }
              icon={Clock}
              sparklineColor="#f59e0b"
            />
            <MetricStatCard
              title="Procesando"
              value={stats?.processing ?? 0}
              subtitle="En el worker ahora"
              icon={Layers}
              sparklineColor="#6366f1"
            />
            <MetricStatCard
              title="Completados"
              value={stats?.done ?? 0}
              subtitle={
                stats?.processing_ms_avg != null
                  ? `latencia media ${Math.round(stats.processing_ms_avg)} ms`
                  : '—'
              }
              icon={CheckCircle2}
              sparklineColor="#10b981"
            />
            <MetricStatCard
              title="Errores"
              value={stats?.error ?? 0}
              subtitle="Tras agotar reintentos"
              icon={XCircle}
              sparklineColor="#f87171"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Encolar trabajo</CardTitle>
              <CardDescription>Imagen o PDF. El resultado se consulta abajo o por webhook.</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (file) create.mutate()
                }}
              >
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Archivo</label>
                  <Input
                    type="file"
                    accept="image/*,application/pdf"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">Idioma</label>
                    <select
                      className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                      value={lang}
                      onChange={(e) => setLang(e.target.value)}
                    >
                      {['es', 'en', 'fr', 'german', 'pt', 'ch'].map((l) => (
                        <option key={l} value={l}>{l}</option>
                      ))}
                    </select>
                  </div>
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">callback_url (opcional)</label>
                    <Input
                      type="url"
                      placeholder="https://mi-app.example/webhooks/ocr"
                      value={callbackUrl}
                      onChange={(e) => setCallbackUrl(e.target.value)}
                    />
                  </div>
                </div>
                <div>
                  <Button type="submit" disabled={!file || create.isPending} className="gap-2">
                    {create.isPending
                      ? <><Loader2 className="h-4 w-4 animate-spin" /> Enviando…</>
                      : <><Send className="h-4 w-4" /> Encolar trabajo</>}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-5 w-5" />
                    Historial
                  </CardTitle>
                  <CardDescription>Trabajos encolados desde el panel y desde la API.</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 gap-2"
                  onClick={() => jobsQuery.refetch()}
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Actualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Archivo</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Idioma</TableHead>
                      <TableHead>Páginas</TableHead>
                      <TableHead>Creado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <TableRow
                        key={job.id}
                        data-state={selected === job.id ? 'selected' : undefined}
                        className="cursor-pointer"
                        onClick={() => setSelected(job.id)}
                      >
                        <TableCell className="font-medium">{job.original_filename ?? job.id.slice(0, 8)}</TableCell>
                        <TableCell><StatusBadge status={job.status} /></TableCell>
                        <TableCell>
                          {job.doc_type ? (
                            <Badge variant="outline">{DOC_TYPE_LABEL[job.doc_type] ?? job.doc_type}</Badge>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell>{job.lang}</TableCell>
                        <TableCell>{job.page_count ?? '—'}</TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {new Date(job.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                    {jobs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground h-24">
                          {jobsQuery.isLoading ? 'Cargando…' : 'Sin trabajos todavía'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
            <PaginationFooter
              currentPage={list?.page ?? 1}
              lastPage={lastPage}
              perPage={list?.per_page ?? PER_PAGE}
              total={total}
              noun="trabajos"
              onPageChange={setPage}
            />
          </Card>

          {selected && detailQuery.data && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  Trabajo {detailQuery.data.id.slice(0, 8)}
                  <StatusBadge status={detailQuery.data.status} />
                </CardTitle>
                {detailQuery.data.callback_status && (
                  <CardDescription>callback: {detailQuery.data.callback_status}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {detailQuery.data.status === 'error' && (
                  <p className="text-sm text-red-600">{detailQuery.data.error}</p>
                )}
                {detailQuery.data.result && (
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                    {detailQuery.data.result.text || '(sin texto detectado)'}
                  </pre>
                )}
                {['pending', 'processing'].includes(detailQuery.data.status) && (
                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> En cola…
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

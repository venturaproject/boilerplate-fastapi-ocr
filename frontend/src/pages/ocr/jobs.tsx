import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { DataTable, DataTablePagination, DataTableViewOptions } from '@/components/data-table'
import { ListFilterPopover } from '@/components/list-filter-popover'
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
import { CheckCircle2, Clock, Layers, Loader2, RefreshCw, Send, X, XCircle } from 'lucide-react'
import { useI18n } from '@/i18n/context'
import { useTableFilters } from '@/hooks/use-table-filters'
import { useColumnReorder } from '@/hooks/use-column-reorder'
import { ExtractionFields } from '@/components/extraction-fields'
import { FormatDownload } from '@/components/format-download'
import { ocrApi, type OcrJobStatus, type OcrJobSummary } from '@/services/ocr-api'
import { DOC_TYPE_LABEL } from './index'
import { buildJobsColumns, jobColumnLabels } from './jobs-columns'

const STATUS_VARIANT: Record<OcrJobStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  pending: 'outline',
  processing: 'secondary',
  done: 'default',
  error: 'destructive',
}

interface JobFilters {
  search?: string
  status?: string
  doc_type?: string
  callback?: string
  page?: string
  per_page?: string
  [key: string]: string | undefined
}

export default function OcrJobs() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const urlFilters = Object.fromEntries(searchParams.entries()) as JobFilters

  const [file, setFile] = useState<File | null>(null)
  const [lang, setLang] = useState('es')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [selected, setSelected] = useState<string | null>(null)

  const {
    filters,
    searchTerm,
    navigate: navigateFilters,
    handleSearch,
    handlePageChange,
    handlePerPageChange,
    perPage,
  } = useTableFilters<JobFilters>({
    basePath: '/admin/ocr/jobs',
    initialFilters: urlFilters,
    initialPerPage: Number(urlFilters.per_page) || 20,
  })

  const page = Number(urlFilters.page) || 1
  const currentPerPage = Number(urlFilters.per_page) || perPage

  const jobsQuery = useQuery({
    queryKey: ['ocr-jobs', urlFilters],
    queryFn: () =>
      ocrApi.listJobs({
        page,
        per_page: currentPerPage,
        status: urlFilters.status,
        doc_type: urlFilters.doc_type,
        search: urlFilters.search,
        callback: urlFilters.callback,
      }),
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

  const redeliver = useMutation({
    mutationFn: (id: string) => ocrApi.redeliver(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ocr-job', selected] })
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
    },
  })

  const create = useMutation({
    mutationFn: () => ocrApi.createJob(file as File, lang, callbackUrl || undefined),
    onSuccess: (job) => {
      setFile(null)
      setCallbackUrl('')
      setSelected(job.id)
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['ocr-stats'] })
    },
  })

  const list = jobsQuery.data
  const jobs: OcrJobSummary[] = list?.data ?? []
  const stats = statsQuery.data
  const total = list?.total ?? 0
  const lastPage = Math.max(1, Math.ceil(total / currentPerPage))

  const columns = buildJobsColumns(t)
  const { columnOrder, columnVisibility, setColumnVisibility, handleDragStart, handleDrop } =
    useColumnReorder(columns.map((c) => c.id as string))

  const table = useReactTable({
    data: jobs,
    columns,
    state: { columnOrder, columnVisibility },
    onColumnOrderChange: () => {},
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const setFilter = (key: keyof JobFilters, value: string) =>
    navigateFilters({ ...filters, [key]: value || undefined, page: '1' })

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
              <CardDescription>
                Imagen o PDF. El resultado se consulta abajo o por webhook.
              </CardDescription>
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
                    {create.isPending ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Enviando…</>
                    ) : (
                      <><Send className="h-4 w-4" /> Encolar trabajo</>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  <CardTitle>Historial</CardTitle>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <Input
                      placeholder={t('filter_placeholder') || 'Buscar…'}
                      value={searchTerm}
                      onChange={(e) => handleSearch(e.target.value)}
                      className="w-64 pr-9"
                    />
                    {searchTerm && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground"
                        onClick={() => handleSearch('')}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                  <ListFilterPopover
                    groups={[
                      {
                        key: 'status',
                        label: 'Estado',
                        allLabel: 'Todos los estados',
                        value: urlFilters.status,
                        options: (['pending', 'processing', 'done', 'error'] as OcrJobStatus[]).map(
                          (s) => ({ value: s, label: s }),
                        ),
                        onChange: (v) => setFilter('status', v ?? ''),
                      },
                      {
                        key: 'doc_type',
                        label: 'Tipo de documento',
                        allLabel: 'Todos los tipos',
                        value: urlFilters.doc_type,
                        options: Object.entries(DOC_TYPE_LABEL).map(([value, label]) => ({
                          value,
                          label,
                        })),
                        onChange: (v) => setFilter('doc_type', v ?? ''),
                      },
                      {
                        key: 'callback',
                        label: 'Webhook',
                        allLabel: 'Cualquiera',
                        value: urlFilters.callback,
                        options: [
                          { value: 'failed', label: 'Con fallo / dead-letter' },
                          { value: 'pending', label: 'Reintento pendiente' },
                        ],
                        onChange: (v) => setFilter('callback', v ?? ''),
                      },
                    ]}
                    onClearAll={() =>
                      navigateFilters({
                        ...filters,
                        status: undefined,
                        doc_type: undefined,
                        callback: undefined,
                        page: '1',
                      })
                    }
                  />
                  <div className="ml-auto flex items-center gap-2">
                    <DataTableViewOptions table={table} columnLabels={jobColumnLabels(t)} />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-9 gap-2"
                      onClick={() => jobsQuery.refetch()}
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> {t('refresh') || 'Actualizar'}
                    </Button>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <DataTable
                  table={table}
                  colCount={columns.length}
                  emptyMessage={jobsQuery.isLoading ? 'Cargando…' : t('no_results') || 'Sin trabajos'}
                  onDragStart={handleDragStart}
                  onDrop={handleDrop}
                  fixedColumnIds={[]}
                  onRowClick={(job) => setSelected(job.id)}
                  isRowActive={(job) => job.id === selected}
                />
              </div>
            </CardContent>
            <DataTablePagination
              currentPage={page}
              lastPage={lastPage}
              perPage={currentPerPage}
              total={total}
              selectedCount={0}
              onPageChange={handlePageChange}
              onPerPageChange={handlePerPageChange}
            />
          </Card>

          {selected && detailQuery.data && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  Trabajo {detailQuery.data.id.slice(0, 8)}
                  <Badge variant={STATUS_VARIANT[detailQuery.data.status]}>
                    {detailQuery.data.status}
                  </Badge>
                </CardTitle>
                {detailQuery.data.callback_url && (
                  <CardDescription>
                    webhook: {detailQuery.data.callback_status ?? 'pendiente'}
                    {detailQuery.data.callback_attempts > 0 &&
                      ` · ${detailQuery.data.callback_attempts} intento(s)`}
                    {detailQuery.data.next_callback_at &&
                      ` · reintento ${new Date(detailQuery.data.next_callback_at).toLocaleString()}`}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                {detailQuery.data.status === 'error' && (
                  <p className="text-sm text-red-600">{detailQuery.data.error}</p>
                )}
                {detailQuery.data.callback_url &&
                  detailQuery.data.callback_status != null &&
                  !detailQuery.data.callback_status.startsWith('http_2') && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      disabled={redeliver.isPending}
                      onClick={() => redeliver.mutate(detailQuery.data!.id)}
                    >
                      {redeliver.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      Reenviar webhook
                    </Button>
                  )}
                <ExtractionFields extraction={detailQuery.data.result?.extraction} />
                {detailQuery.data.status === 'done' && (
                  <FormatDownload
                    formats={['text', 'hocr', 'alto']}
                    baseName={(detailQuery.data.original_filename ?? detailQuery.data.id).replace(/\.[^.]+$/, '')}
                    getBlob={(fmt) => ocrApi.jobAs(detailQuery.data!.id, fmt as 'text' | 'hocr' | 'alto')}
                  />
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

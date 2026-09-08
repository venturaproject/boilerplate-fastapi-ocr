import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { DataTable, DataTablePagination, DataTableViewOptions } from '@/components/data-table'
import { ListFilterPopover } from '@/components/list-filter-popover'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Clock, FileText, Layers, Loader2, RefreshCw, Timer, Trash2, X } from 'lucide-react'
import { useI18n } from '@/i18n/context'
import { useTableFilters } from '@/hooks/use-table-filters'
import { useColumnReorder } from '@/hooks/use-column-reorder'
import { usePermission } from '@/hooks/use-permission'
import { ExtractionFields } from '@/components/extraction-fields'
import { documentsApi, type DocumentRow } from '@/services/documents-api'
import { DOC_TYPE_LABEL } from '@/pages/ocr/index'
import {
  buildDocumentsColumns,
  documentColumnLabels,
  MODE_LABEL,
  STATUS_VARIANT,
} from './columns'

interface DocFilters {
  search?: string
  mode?: string
  doc_type?: string
  status?: string
  page?: string
  per_page?: string
  [key: string]: string | undefined
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function DocumentsPage() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { can } = usePermission()
  const canDelete = can('documents.delete')
  const [searchParams] = useSearchParams()
  const urlFilters = Object.fromEntries(searchParams.entries()) as DocFilters
  const [selected, setSelected] = useState<string | null>(null)

  const {
    filters,
    searchTerm,
    navigate: navigateFilters,
    handleSearch,
    handlePageChange,
    handlePerPageChange,
    perPage,
  } = useTableFilters<DocFilters>({
    basePath: '/admin/documents',
    initialFilters: urlFilters,
    initialPerPage: Number(urlFilters.per_page) || 20,
  })

  const page = Number(urlFilters.page) || 1
  const currentPerPage = Number(urlFilters.per_page) || perPage

  const listQuery = useQuery({
    queryKey: ['documents', urlFilters],
    queryFn: () =>
      documentsApi.list({
        page,
        per_page: currentPerPage,
        search: urlFilters.search,
        mode: urlFilters.mode,
        doc_type: urlFilters.doc_type,
        status: urlFilters.status,
      }),
    refetchInterval: (query) =>
      query.state.data?.data.some((d) => d.status === 'pending') ? 3000 : false,
  })

  const detailQuery = useQuery({
    queryKey: ['document', selected],
    queryFn: () => documentsApi.detail(selected as string),
    enabled: !!selected,
  })

  const statsQuery = useQuery({
    queryKey: ['documents-stats'],
    queryFn: () => documentsApi.stats(),
    refetchInterval: 10000,
  })

  const remove = useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => {
      setSelected(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['documents-stats'] })
    },
  })

  const list = listQuery.data
  const rows: DocumentRow[] = list?.data ?? []
  const stats = statsQuery.data
  const detail = detailQuery.data
  const total = list?.total ?? 0
  const lastPage = Math.max(1, Math.ceil(total / currentPerPage))

  const columns = buildDocumentsColumns(t)
  const { columnOrder, columnVisibility, setColumnVisibility, handleDragStart, handleDrop } =
    useColumnReorder(columns.map((c) => c.id as string))

  const table = useReactTable({
    data: rows,
    columns,
    state: { columnOrder, columnVisibility },
    onColumnOrderChange: () => {},
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const setFilter = (key: keyof DocFilters, value: string) =>
    navigateFilters({ ...filters, [key]: value || undefined, page: '1' })

  return (
    <AuthenticatedLayout title="Documentos OCR">
      <Main>
        <div className="grid flex-1 items-start gap-4 md:gap-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Documentos procesados</h2>
            <p className="text-muted-foreground">
              Registro de cada documento procesado por la API de OCR — llamadas síncronas,
              clasificaciones y trabajos asíncronos.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricStatCard
              title="Total"
              value={stats?.total ?? 0}
              subtitle="Documentos registrados"
              icon={FileText}
              sparklineColor="#6366f1"
            />
            <MetricStatCard
              title="Últimas 24 h"
              value={stats?.last_24h ?? 0}
              subtitle="Procesados recientemente"
              icon={Clock}
              sparklineColor="#10b981"
            />
            <MetricStatCard
              title="Síncronos"
              value={stats?.by_mode.sync ?? 0}
              subtitle={`${stats?.by_mode.async ?? 0} asíncronos · ${stats?.by_mode.classify ?? 0} clasificaciones`}
              icon={Layers}
              sparklineColor="#f59e0b"
            />
            <MetricStatCard
              title="Latencia media"
              value={
                stats?.processing_ms_avg != null ? `${Math.round(stats.processing_ms_avg)} ms` : '—'
              }
              subtitle={
                stats?.processing_ms_p95 != null
                  ? `p95 ${Math.round(stats.processing_ms_p95)} ms`
                  : 'Sin datos'
              }
              icon={Timer}
              sparklineColor="#3b82f4"
            />
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
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
                        key: 'mode',
                        label: 'Modo',
                        allLabel: 'Todos los modos',
                        value: urlFilters.mode,
                        options: Object.entries(MODE_LABEL).map(([value, label]) => ({
                          value,
                          label,
                        })),
                        onChange: (v) => setFilter('mode', v ?? ''),
                      },
                      {
                        key: 'status',
                        label: 'Estado',
                        allLabel: 'Todos los estados',
                        value: urlFilters.status,
                        options: [
                          { value: 'pending', label: 'pending' },
                          { value: 'done', label: 'done' },
                          { value: 'error', label: 'error' },
                        ],
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
                    ]}
                    onClearAll={() =>
                      navigateFilters({
                        ...filters,
                        mode: undefined,
                        status: undefined,
                        doc_type: undefined,
                        page: '1',
                      })
                    }
                  />
                  <div className="ml-auto flex items-center gap-2">
                    <DataTableViewOptions table={table} columnLabels={documentColumnLabels(t)} />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-9 gap-2"
                      onClick={() => listQuery.refetch()}
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> {t('refresh') || 'Actualizar'}
                    </Button>
                  </div>
                </div>
              </div>
              <CardDescription>Cada llamada a la API de OCR queda registrada aquí.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <DataTable
                  table={table}
                  colCount={columns.length}
                  emptyMessage={listQuery.isLoading ? 'Cargando…' : t('no_results') || 'Sin documentos'}
                  onDragStart={handleDragStart}
                  onDrop={handleDrop}
                  fixedColumnIds={[]}
                  onRowClick={(doc) => setSelected(doc.id)}
                  isRowActive={(doc) => doc.id === selected}
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

        </div>
      </Main>

      <Sheet open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          {detailQuery.isLoading && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
            </p>
          )}
          {detail && (
            <>
              <SheetHeader>
                <div className="flex flex-col gap-2 pr-8 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <SheetTitle className="flex items-center gap-2">
                      <span className="truncate">{detail.original_filename ?? detail.id.slice(0, 8)}</span>
                      <Badge variant={STATUS_VARIANT[detail.status]}>{detail.status}</Badge>
                    </SheetTitle>
                    <SheetDescription>
                      {MODE_LABEL[detail.mode]} · {formatBytes(detail.size_bytes)}
                      {detail.processing_ms != null && ` · ${detail.processing_ms} ms`}
                      {detail.char_count != null && ` · ${detail.char_count} caracteres`}
                      {detail.ocr_job_id && ` · job ${detail.ocr_job_id.slice(0, 8)}`}
                    </SheetDescription>
                  </div>
                  {canDelete && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="sm" className="gap-2 text-destructive">
                          <Trash2 className="h-4 w-4" /> Borrar
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>¿Borrar este registro?</AlertDialogTitle>
                          <AlertDialogDescription>
                            Se elimina el registro del documento. El trabajo OCR asociado (si lo
                            hay) no se ve afectado.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancelar</AlertDialogCancel>
                          <AlertDialogAction onClick={() => remove.mutate(detail.id)}>
                            {remove.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              'Borrar'
                            )}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                {detail.status === 'error' && detail.error && (
                  <p className="text-sm text-red-600">{detail.error}</p>
                )}
                <ExtractionFields extraction={detail.extraction} />
                {detail.text_excerpt ? (
                  <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                    {detail.text_excerpt}
                  </pre>
                ) : (
                  detail.status !== 'error' && (
                    <p className="text-sm text-muted-foreground">
                      {detail.status === 'pending'
                        ? 'En cola…'
                        : 'Sin extracto de texto guardado.'}
                    </p>
                  )
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </AuthenticatedLayout>
  )
}

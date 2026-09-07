import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { PaginationFooter } from '@/components/pagination-footer'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { Clock, FileText, Layers, Loader2, RefreshCw, Timer, Trash2 } from 'lucide-react'
import { usePermission } from '@/hooks/use-permission'
import {
  documentsApi,
  type DocumentMode,
  type DocumentRow,
  type DocumentStatus,
} from '@/services/documents-api'
import { DOC_TYPE_LABEL } from '@/pages/ocr/index'

const PER_PAGE = 20

const MODE_LABEL: Record<DocumentMode, string> = {
  sync: 'Síncrono',
  async: 'Asíncrono',
  classify: 'Clasificación',
}

const STATUS_VARIANT: Record<DocumentStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  pending: 'outline',
  done: 'default',
  error: 'destructive',
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const { can } = usePermission()
  const canDelete = can('documents.delete')

  const [search, setSearch] = useState('')
  const [mode, setMode] = useState('')
  const [docType, setDocType] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)

  const setFilter = (setter: (v: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }

  const filters = {
    search: search || undefined,
    mode: mode || undefined,
    doc_type: docType || undefined,
    status: status || undefined,
    page,
    per_page: PER_PAGE,
  }

  const listQuery = useQuery({
    queryKey: ['documents', filters],
    queryFn: () => documentsApi.list(filters),
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
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Historial
                  </CardTitle>
                  <CardDescription>
                    Cada llamada a la API de OCR queda registrada aquí.
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    placeholder="Buscar por nombre…"
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value)
                      setPage(1)
                    }}
                    className="w-full sm:w-56"
                  />
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={mode}
                    onChange={(e) => setFilter(setMode)(e.target.value)}
                  >
                    <option value="">Todos los modos</option>
                    {Object.entries(MODE_LABEL).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={status}
                    onChange={(e) => setFilter(setStatus)(e.target.value)}
                  >
                    <option value="">Todos los estados</option>
                    <option value="pending">Pendiente</option>
                    <option value="done">Completado</option>
                    <option value="error">Error</option>
                  </select>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={docType}
                    onChange={(e) => setFilter(setDocType)(e.target.value)}
                  >
                    <option value="">Todos los tipos</option>
                    {Object.entries(DOC_TYPE_LABEL).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9 gap-2"
                    onClick={() => listQuery.refetch()}
                  >
                    <RefreshCw className="h-3.5 w-3.5" /> Actualizar
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Archivo</TableHead>
                      <TableHead>Modo</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Idioma</TableHead>
                      <TableHead>Páginas</TableHead>
                      <TableHead>Creado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((doc) => (
                      <TableRow
                        key={doc.id}
                        data-state={selected === doc.id ? 'selected' : undefined}
                        className="cursor-pointer"
                        onClick={() => setSelected(doc.id)}
                      >
                        <TableCell className="font-medium">
                          {doc.original_filename ?? doc.id.slice(0, 8)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{MODE_LABEL[doc.mode]}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={STATUS_VARIANT[doc.status]}>{doc.status}</Badge>
                        </TableCell>
                        <TableCell>
                          {doc.doc_type ? (
                            <Badge variant="outline">
                              {DOC_TYPE_LABEL[doc.doc_type] ?? doc.doc_type}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell>{doc.lang}</TableCell>
                        <TableCell>{doc.page_count ?? '—'}</TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {new Date(doc.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                    {rows.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground h-24">
                          {listQuery.isLoading ? 'Cargando…' : 'Sin documentos'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
            <PaginationFooter
              currentPage={list?.current_page ?? 1}
              lastPage={list?.last_page ?? 1}
              perPage={list?.per_page ?? PER_PAGE}
              total={list?.total ?? 0}
              noun="documentos"
              onPageChange={setPage}
            />
          </Card>

          {selected && detail && (
            <Card>
              <CardHeader>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-base">
                      {detail.original_filename ?? detail.id.slice(0, 8)}
                      <Badge variant={STATUS_VARIANT[detail.status]}>{detail.status}</Badge>
                    </CardTitle>
                    <CardDescription>
                      {MODE_LABEL[detail.mode]} · {formatBytes(detail.size_bytes)}
                      {detail.processing_ms != null && ` · ${detail.processing_ms} ms`}
                      {detail.char_count != null && ` · ${detail.char_count} caracteres`}
                      {detail.ocr_job_id && ` · job ${detail.ocr_job_id.slice(0, 8)}`}
                    </CardDescription>
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
              </CardHeader>
              <CardContent>
                {detail.status === 'error' && detail.error && (
                  <p className="text-sm text-red-600">{detail.error}</p>
                )}
                {detail.text_excerpt ? (
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                    {detail.text_excerpt}
                  </pre>
                ) : (
                  detail.status !== 'error' && (
                    <p className="text-muted-foreground text-sm">
                      {detail.status === 'pending'
                        ? 'En cola…'
                        : 'Sin extracto de texto guardado.'}
                    </p>
                  )
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

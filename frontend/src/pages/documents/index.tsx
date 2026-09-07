import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { usePermission } from '@/hooks/use-permission'
import {
  documentsApi,
  type DocumentMode,
  type DocumentRow,
  type DocumentStatus,
} from '@/services/documents-api'
import { DOC_TYPE_LABEL } from '@/pages/ocr/index'

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
  const [selected, setSelected] = useState<string | null>(null)

  const filters = {
    search: search || undefined,
    mode: mode || undefined,
    doc_type: docType || undefined,
    status: status || undefined,
    per_page: 50,
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

  const rows: DocumentRow[] = listQuery.data?.data ?? []
  const stats = statsQuery.data
  const detail = detailQuery.data

  return (
    <AuthenticatedLayout title="Documentos OCR">
      <Main>
        <div className="grid flex-1 items-start gap-6 md:gap-8 max-w-5xl">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Documentos procesados</h2>
            <p className="text-muted-foreground mt-1">
              Registro de cada documento procesado por la API de OCR — llamadas síncronas,
              clasificaciones y trabajos asíncronos.
            </p>
          </div>

          {stats && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'Total', value: stats.total },
                { label: 'Últimas 24 h', value: stats.last_24h },
                { label: 'Síncronos', value: stats.by_mode.sync ?? 0 },
                { label: 'Asíncronos', value: stats.by_mode.async ?? 0 },
              ].map((s) => (
                <Card key={s.label}>
                  <CardContent className="p-4">
                    <div className="text-2xl font-semibold tabular-nums">{s.value}</div>
                    <div className="text-xs text-muted-foreground">{s.label}</div>
                  </CardContent>
                </Card>
              ))}
              {stats.processing_ms_avg != null && (
                <p className="col-span-2 text-xs text-muted-foreground sm:col-span-4">
                  Latencia media {Math.round(stats.processing_ms_avg)} ms
                  {stats.processing_ms_p95 != null &&
                    ` · p95 ${Math.round(stats.processing_ms_p95)} ms`}
                </p>
              )}
            </div>
          )}

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Historial</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => listQuery.refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" /> Actualizar
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2 sm:grid-cols-4">
                <Input
                  placeholder="Buscar por nombre…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {[
                  { value: mode, set: setMode, label: 'Todos los modos', options: Object.entries(MODE_LABEL) },
                  {
                    value: status,
                    set: setStatus,
                    label: 'Todos los estados',
                    options: [
                      ['pending', 'Pendiente'],
                      ['done', 'Completado'],
                      ['error', 'Error'],
                    ] as [string, string][],
                  },
                  {
                    value: docType,
                    set: setDocType,
                    label: 'Todos los tipos',
                    options: Object.entries(DOC_TYPE_LABEL),
                  },
                ].map((s, i) => (
                  <select
                    key={i}
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={s.value}
                    onChange={(e) => s.set(e.target.value)}
                  >
                    <option value="">{s.label}</option>
                    {s.options.map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                ))}
              </div>

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
          </Card>

          {selected && detail && (
            <Card>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">
                    {detail.original_filename ?? detail.id.slice(0, 8)}
                    <span className="ml-2">
                      <Badge variant={STATUS_VARIANT[detail.status]}>{detail.status}</Badge>
                    </span>
                  </CardTitle>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {MODE_LABEL[detail.mode]} · {formatBytes(detail.size_bytes)}
                    {detail.processing_ms != null && ` · ${detail.processing_ms} ms`}
                    {detail.char_count != null && ` · ${detail.char_count} caracteres`}
                    {detail.ocr_job_id && ` · job ${detail.ocr_job_id.slice(0, 8)}`}
                  </p>
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

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
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
import { Loader2, RefreshCw, Send } from 'lucide-react'
import { ocrApi, type OcrJobStatus, type OcrJobSummary } from '@/services/ocr-api'

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
  const [selected, setSelected] = useState<string | null>(null)

  const jobsQuery = useQuery({
    queryKey: ['ocr-jobs'],
    queryFn: () => ocrApi.listJobs({ per_page: 50 }),
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
      setSelected(job.id)
      queryClient.invalidateQueries({ queryKey: ['ocr-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['ocr-stats'] })
    },
  })

  const jobs: OcrJobSummary[] = jobsQuery.data?.data ?? []
  const stats = statsQuery.data

  return (
    <AuthenticatedLayout title="Trabajos OCR">
      <Main>
        <div className="grid flex-1 items-start gap-6 md:gap-8 max-w-5xl">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Trabajos OCR (asíncrono)</h2>
            <p className="text-muted-foreground mt-1">
              Encola documentos; el worker los procesa en segundo plano. Si indicas un
              <code className="mx-1 rounded bg-muted px-1">callback_url</code>
              recibirás el resultado por webhook.
            </p>
          </div>

          {stats && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'En cola', value: stats.pending },
                { label: 'Procesando', value: stats.processing },
                { label: 'Completados', value: stats.done },
                { label: 'Errores', value: stats.error },
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
                  {stats.processing_ms_p95 != null && ` · p95 ${Math.round(stats.processing_ms_p95)} ms`}
                  {stats.oldest_pending_age_seconds != null &&
                    ` · pendiente más antiguo hace ${Math.round(stats.oldest_pending_age_seconds)} s`}
                </p>
              )}
            </div>
          )}

          <Card>
            <CardContent className="pt-6">
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
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Historial</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => jobsQuery.refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" /> Actualizar
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Archivo</TableHead>
                      <TableHead>Estado</TableHead>
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
                        <TableCell className="font-medium">{job.original_filename ?? job.id}</TableCell>
                        <TableCell><StatusBadge status={job.status} /></TableCell>
                        <TableCell>{job.lang}</TableCell>
                        <TableCell>{job.page_count ?? '—'}</TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {new Date(job.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                    {jobs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground h-24">
                          {jobsQuery.isLoading ? 'Cargando…' : 'Sin trabajos todavía'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {selected && detailQuery.data && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Trabajo {detailQuery.data.id.slice(0, 8)}
                  <span className="ml-2"><StatusBadge status={detailQuery.data.status} /></span>
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

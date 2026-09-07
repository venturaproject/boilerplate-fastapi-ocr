import { useState } from 'react'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { router } from '@/lib/router-singleton'
import { pathFor } from '@/lib/app-routes'
import { PageProps } from '@/types'
import {
  BrainCircuit,
  Search,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react'

interface Interpretacion {
  entidadObjetivo: string
  textoDepurado: string
  terminos: string[]
  filtrosPropuestos: Record<string, string | null>
  confianza: number
  observaciones: string
}

interface ResultadoDispositivo {
  id: number
  marca: string
  modelo: string
  imei: string | null
  numero: string | null
  grupo: string | null
  empleado: string | null
  motivoCoincidencia: string
}

interface ConsultaAsistidaPageProps extends PageProps {
  interpretacion: Interpretacion | null
  resultados: ResultadoDispositivo[]
  prompt: string
  error: string | null
}

const SUGERENCIAS = [
  'Muéstrame todos los Samsung sin asignar',
  'Tabletas disponibles de cualquier marca',
  'Dispositivos asignados a empleados con IMEI',
  'iPhones en uso actualmente',
  'Bases Wifi disponibles',
]

function ConfianzaBadge({ valor }: { valor: number }) {
  const pct = Math.round(valor * 100)
  const variant = valor >= 0.7 ? 'default' : valor >= 0.4 ? 'secondary' : 'outline'
  return (
    <Badge variant={variant} className="tabular-nums">
      {pct}% confianza
    </Badge>
  )
}

function InterpretacionPanel({ data }: { data: Interpretacion }) {
  const [expanded, setExpanded] = useState(true)

  const filtrosActivos = Object.entries(data.filtrosPropuestos).filter(
    ([, v]) => v !== null && v !== ''
  )

  const grupoLabel = (val: string | null) => {
    if (val === '0') return 'Sin asignar'
    if (val === '1') return 'Asignado'
    return val
  }

  return (
    <Card className="border-blue-200 bg-blue-50/40 dark:border-blue-900 dark:bg-blue-950/20">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <CardTitle className="text-sm font-medium text-blue-800 dark:text-blue-300">
              Interpretación de la consulta
            </CardTitle>
            <ConfianzaBadge valor={data.confianza} />
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-muted-foreground"
            onClick={() => setExpanded((p) => !p)}
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </Button>
        </div>
        {data.textoDepurado && (
          <CardDescription className="text-blue-700/80 dark:text-blue-400/70 italic">
            &ldquo;{data.textoDepurado}&rdquo;
          </CardDescription>
        )}
      </CardHeader>

      {expanded && (
        <CardContent className="grid gap-3 pt-0 text-sm">
          {data.terminos.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Términos:</span>
              {data.terminos.map((t) => (
                <Badge key={t} variant="outline" className="text-xs">
                  {t}
                </Badge>
              ))}
            </div>
          )}

          {filtrosActivos.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Filtros aplicados:</span>
              {filtrosActivos.map(([k, v]) => (
                <Badge key={k} className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border-0">
                  {k === 'grupo' ? grupoLabel(v) : `${k}: ${v}`}
                </Badge>
              ))}
            </div>
          )}

          {data.observaciones && (
            <p className="text-xs text-muted-foreground border-t pt-2">{data.observaciones}</p>
          )}
        </CardContent>
      )}
    </Card>
  )
}

export default function ConsultaAsistida({
  interpretacion,
  resultados,
  prompt: initialPrompt,
  error,
}: ConsultaAsistidaPageProps) {
  const [prompt, setPrompt] = useState(initialPrompt)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || loading) return

    router.post(
      pathFor('admin.consulta-asistida.buscar'),
      { prompt: prompt.trim() },
      {
        preserveScroll: true,
        onStart: () => setLoading(true),
        onFinish: () => setLoading(false),
      }
    )
  }

  const handleSugerencia = (texto: string) => {
    setPrompt(texto)
  }

  const hasResults = resultados.length > 0

  return (
    <AuthenticatedLayout title="Búsqueda asistida">
      <Main>
        <div className="grid flex-1 items-start gap-6 md:gap-8 max-w-5xl">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2">
              <BrainCircuit className="h-6 w-6 text-primary" />
              <h2 className="text-2xl font-bold tracking-tight">Búsqueda asistida</h2>
            </div>
            <p className="text-muted-foreground mt-1">
              Describe en lenguaje natural lo que buscas. La IA interpreta tu consulta y busca en los datos reales.
            </p>
          </div>

          {/* Search form */}
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <Textarea
                  placeholder="Ej: Muéstrame todos los Samsung sin asignar, o tabletas disponibles..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={3}
                  className="resize-none text-base"
                  disabled={loading}
                />
                <div className="flex items-center justify-between gap-4">
                  <div className="flex flex-wrap gap-1.5">
                    {SUGERENCIAS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => handleSugerencia(s)}
                        className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition-colors"
                        disabled={loading}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                  <Button
                    type="submit"
                    disabled={!prompt.trim() || loading}
                    className="shrink-0 gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Interpretando...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4" />
                        Buscar
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Interpretation panel */}
          {interpretacion && <InterpretacionPanel data={interpretacion} />}

          {/* Results */}
          {(interpretacion || hasResults) && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-muted-foreground" />
                  <CardTitle className="text-base">
                    Dispositivos encontrados
                    {hasResults && (
                      <Badge variant="secondary" className="ml-2 text-xs">
                        {resultados.length}
                      </Badge>
                    )}
                  </CardTitle>
                </div>
                {hasResults && (
                  <CardDescription>
                    Resultados reales obtenidos según los filtros interpretados.
                    No son generados por IA.
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="p-0">
                {!hasResults ? (
                  <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">
                    No se encontraron dispositivos con estos criterios.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Marca</TableHead>
                        <TableHead>Modelo</TableHead>
                        <TableHead>IMEI</TableHead>
                        <TableHead>Número</TableHead>
                        <TableHead>Grupo</TableHead>
                        <TableHead>Empleado</TableHead>
                        <TableHead>Coincidencia</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {resultados.map((r) => (
                        <TableRow key={r.id}>
                          <TableCell className="font-medium">{r.marca}</TableCell>
                          <TableCell>{r.modelo}</TableCell>
                          <TableCell className="font-mono text-xs text-muted-foreground">
                            {r.imei ?? '—'}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {r.numero ?? '—'}
                          </TableCell>
                          <TableCell>
                            {r.grupo ? (
                              <Badge variant="outline" className="text-xs">{r.grupo}</Badge>
                            ) : (
                              <span className="text-muted-foreground text-xs">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {r.empleado ? (
                              <span className="text-sm">{r.empleado}</span>
                            ) : (
                              <Badge variant="secondary" className="text-xs">Sin asignar</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <span className="text-xs text-muted-foreground">{r.motivoCoincidencia}</span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

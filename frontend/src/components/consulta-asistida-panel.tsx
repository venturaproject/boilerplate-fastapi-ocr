import { useState } from 'react'
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
import {
  BrainCircuit,
  Search,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  ExternalLink,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'

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

const SUGERENCIAS = [
  'Samsung sin asignar',
  'Tabletas disponibles',
  'iPhones en uso',
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
  const filtrosActivos = Object.entries(data.filtrosPropuestos).filter(([, v]) => v !== null && v !== '')
  const grupoLabel = (val: string | null) => val === '0' ? 'Sin asignar' : val === '1' ? 'Asignado' : val

  return (
    <Card className="border-blue-200 bg-blue-50/40 dark:border-blue-900 dark:bg-blue-950/20">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <CardTitle className="text-sm font-medium text-blue-800 dark:text-blue-300">
              Interpretación
            </CardTitle>
            <ConfianzaBadge valor={data.confianza} />
          </div>
          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setExpanded(p => !p)}>
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
        <CardContent className="grid gap-2 pt-0 text-sm">
          {data.terminos.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Términos:</span>
              {data.terminos.map(t => <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
            </div>
          )}
          {filtrosActivos.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Filtros:</span>
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

export function ConsultaAsistidaPanel() {
  const navigate = useNavigate()
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [interpretacion, setInterpretacion] = useState<Interpretacion | null>(null)
  const [resultados, setResultados] = useState<ResultadoDispositivo[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || loading) return

    setLoading(true)
    setError(null)

    try {
      const { data } = await axios.post(endpoints.consultaAsistida.query, { prompt: prompt.trim() })
      setInterpretacion(data.interpretacion)
      setResultados(data.resultados)
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.error ?? 'No se pudo conectar con el servidor.')
      setInterpretacion(null)
      setResultados([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Búsqueda asistida por IA</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-muted-foreground"
          onClick={() => navigate('/admin/consulta-asistida')}
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Vista completa
        </Button>
      </div>

      <Card>
        <CardContent className="pt-5">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <Textarea
              placeholder="Ej: Samsung sin asignar, tabletas disponibles..."
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              rows={2}
              className="resize-none"
              disabled={loading}
            />
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-wrap gap-2">
                {SUGERENCIAS.map(s => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setPrompt(s)}
                    disabled={loading}
                    className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <Button type="submit" disabled={!prompt.trim() || loading} size="sm" className="shrink-0 gap-2">
                {loading
                  ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Interpretando...</>
                  : <><Search className="h-3.5 w-3.5" />Buscar</>
                }
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {interpretacion && <InterpretacionPanel data={interpretacion} />}

      {resultados.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">
                Dispositivos encontrados
                <Badge variant="secondary" className="ml-2 text-xs">{resultados.length}</Badge>
              </CardTitle>
            </div>
            <CardDescription className="text-xs">Resultados reales — no generados por IA.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Marca</TableHead>
                  <TableHead>Modelo</TableHead>
                  <TableHead>IMEI</TableHead>
                  <TableHead>Empleado</TableHead>
                  <TableHead>Coincidencia</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resultados.map(r => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.marca}</TableCell>
                    <TableCell>{r.modelo}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{r.imei ?? '—'}</TableCell>
                    <TableCell>
                      {r.empleado
                        ? <span className="text-sm">{r.empleado}</span>
                        : <Badge variant="secondary" className="text-xs">Sin asignar</Badge>
                      }
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{r.motivoCoincidencia}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

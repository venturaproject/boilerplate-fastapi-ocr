import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
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
import { AlertCircle, FileScan, Loader2, ScanText } from 'lucide-react'
import { ExtractionFields } from '@/components/extraction-fields'
import { FormatDownload } from '@/components/format-download'
import { ocrApi, type OcrResult } from '@/services/ocr-api'

export const DOC_TYPE_LABEL: Record<string, string> = {
  invoice: 'Factura',
  cv: 'CV',
  payslip: 'Nómina',
  contract: 'Contrato',
  id_document: 'Documento identidad',
  bank_statement: 'Extracto bancario',
  delivery_note: 'Albarán',
  receipt: 'Recibo / ticket',
}

const LANGS = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'Inglés' },
  { value: 'fr', label: 'Francés' },
  { value: 'german', label: 'Alemán' },
  { value: 'pt', label: 'Portugués' },
  { value: 'ch', label: 'Chino' },
]

function confidenceVariant(score: number) {
  if (score >= 0.9) return 'default'
  if (score >= 0.7) return 'secondary'
  return 'outline'
}

export default function OcrPlayground() {
  const [file, setFile] = useState<File | null>(null)
  const [lang, setLang] = useState('es')

  const scan = useMutation({
    mutationFn: () => ocrApi.scan(file as File, lang),
  })

  const result: OcrResult | undefined = scan.data

  return (
    <AuthenticatedLayout title="OCR">
      <Main>
        <div className="grid flex-1 items-start gap-6 md:gap-8 max-w-5xl">
          <div>
            <div className="flex items-center gap-2">
              <ScanText className="h-6 w-6 text-primary" />
              <h2 className="text-2xl font-bold tracking-tight">OCR — reconocimiento de texto</h2>
            </div>
            <p className="text-muted-foreground mt-1">
              Sube una imagen o un PDF y PaddleOCR devolverá el texto detectado, con posición y
              confianza por línea. Para lotes o documentos grandes usa los{' '}
              <a href="/admin/ocr/jobs" className="underline underline-offset-2">trabajos asíncronos</a>.
            </p>
          </div>

          <Card>
            <CardContent className="pt-6">
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (file) scan.mutate()
                }}
              >
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Archivo (PNG, JPEG, WEBP, BMP, TIFF o PDF)</label>
                  <Input
                    type="file"
                    accept="image/*,application/pdf"
                    onChange={(e) => {
                      setFile(e.target.files?.[0] ?? null)
                      scan.reset()
                    }}
                  />
                </div>

                <div className="grid gap-2 max-w-xs">
                  <label className="text-sm font-medium">Idioma</label>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={lang}
                    onChange={(e) => setLang(e.target.value)}
                  >
                    {LANGS.map((l) => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <Button type="submit" disabled={!file || scan.isPending} className="gap-2">
                    {scan.isPending ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Procesando…</>
                    ) : (
                      <><FileScan className="h-4 w-4" /> Reconocer texto</>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {scan.isError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                {(scan.error as any)?.response?.data?.detail ?? 'No se pudo procesar el archivo.'}
              </span>
            </div>
          )}

          {result && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Texto extraído</CardTitle>
                  <CardDescription>
                    Motor <Badge variant="outline">{result.engine}</Badge>{' '}
                    · idioma <Badge variant="outline">{result.lang}</Badge>{' '}
                    · {result.page_count} página(s) · {result.processing_ms} ms
                    {result.cached && <> · <Badge variant="secondary">desde caché</Badge></>}
                    {result.classification?.doc_type && (
                      <> · tipo{' '}
                        <Badge>
                          {DOC_TYPE_LABEL[result.classification.doc_type] ?? result.classification.doc_type}
                          {' '}({Math.round(result.classification.confidence * 100)}%)
                        </Badge>
                      </>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ExtractionFields extraction={result.extraction} />
                  {file && (
                    <FormatDownload
                      formats={['text', 'hocr', 'alto', 'pdf']}
                      baseName={file.name.replace(/\.[^.]+$/, '')}
                      getBlob={(fmt) => ocrApi.scanAs(file, fmt, lang)}
                    />
                  )}
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                    {result.text || '(sin texto detectado)'}
                  </pre>
                </CardContent>
              </Card>

              {result.pages.map((page) => (
                <Card key={page.page}>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Página {page.page}
                      <span className="ml-2 text-muted-foreground font-normal">
                        {page.width}×{page.height}px · {page.lines.length} línea(s)
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-16">#</TableHead>
                            <TableHead>Texto</TableHead>
                            <TableHead className="w-32">Confianza</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {page.lines.map((line, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                              <TableCell className="font-medium">{line.text}</TableCell>
                              <TableCell>
                                <Badge variant={confidenceVariant(line.confidence)} className="tabular-nums">
                                  {(line.confidence * 100).toFixed(1)}%
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                          {page.lines.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={3} className="text-center text-muted-foreground">
                                Sin líneas detectadas
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          )}
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

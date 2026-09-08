import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { downloadBlob } from '@/lib/download'

const EXT: Record<string, string> = { text: 'txt', hocr: 'hocr.html', alto: 'alto.xml', pdf: 'pdf' }

interface FormatDownloadProps {
  formats: Array<'text' | 'hocr' | 'alto' | 'pdf'>
  baseName: string
  getBlob: (fmt: 'text' | 'hocr' | 'alto' | 'pdf') => Promise<Blob>
}

/** A row of "descargar como …" buttons for the OCR output formats. */
export function FormatDownload({ formats, baseName, getBlob }: FormatDownloadProps) {
  const [busy, setBusy] = useState<string | null>(null)

  const handle = async (fmt: 'text' | 'hocr' | 'alto' | 'pdf') => {
    setBusy(fmt)
    try {
      const blob = await getBlob(fmt)
      downloadBlob(blob, `${baseName}.${EXT[fmt]}`)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">Descargar:</span>
      {formats.map((fmt) => (
        <Button
          key={fmt}
          variant="outline"
          size="sm"
          className="h-7 gap-1 text-xs uppercase"
          disabled={busy !== null}
          onClick={() => handle(fmt)}
        >
          {busy === fmt ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Download className="h-3 w-3" />
          )}
          {fmt}
        </Button>
      ))}
    </div>
  )
}

import { createColumnHelper } from '@tanstack/react-table'
import { Badge } from '@/components/ui/badge'
import type { OcrJobStatus, OcrJobSummary } from '@/services/ocr-api'
import { DOC_TYPE_LABEL } from './index'

const STATUS_VARIANT: Record<OcrJobStatus, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  pending: 'outline',
  processing: 'secondary',
  done: 'default',
  error: 'destructive',
}

function formatBytes(n: number): string {
  if (!n) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

const col = createColumnHelper<OcrJobSummary>()

export function buildJobsColumns(t: (k: string) => string) {
  return [
    col.accessor('original_filename', {
      id: 'original_filename',
      header: () => t('col_file') || 'Archivo',
      cell: (info) => (
        <span className="font-medium">{info.getValue() ?? info.row.original.id.slice(0, 8)}</span>
      ),
    }),
    col.accessor('status', {
      id: 'status',
      header: () => t('col_status') || 'Estado',
      cell: (info) => <Badge variant={STATUS_VARIANT[info.getValue()]}>{info.getValue()}</Badge>,
    }),
    col.accessor('doc_type', {
      id: 'doc_type',
      header: () => t('col_type') || 'Tipo',
      cell: (info) => {
        const v = info.getValue()
        return v ? (
          <Badge variant="outline">{DOC_TYPE_LABEL[v] ?? v}</Badge>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        )
      },
    }),
    col.accessor('lang', {
      id: 'lang',
      header: () => t('col_lang') || 'Idioma',
      cell: (info) => info.getValue(),
    }),
    col.accessor('page_count', {
      id: 'page_count',
      header: () => t('col_pages') || 'Páginas',
      cell: (info) => info.getValue() ?? '—',
    }),
    col.accessor('size_bytes', {
      id: 'size_bytes',
      header: () => t('col_size') || 'Tamaño',
      cell: (info) => (
        <span className="text-muted-foreground text-xs">{formatBytes(info.getValue())}</span>
      ),
    }),
    col.accessor('processing_ms', {
      id: 'processing_ms',
      header: () => t('col_latency') || 'Latencia',
      cell: (info) => {
        const v = info.getValue()
        return v != null ? `${v} ms` : '—'
      },
    }),
    col.accessor('created_at', {
      id: 'created_at',
      header: () => t('col_created') || 'Creado',
      cell: (info) => (
        <span className="text-muted-foreground text-xs">
          {new Date(info.getValue()).toLocaleString()}
        </span>
      ),
    }),
  ]
}

export const jobColumnLabels = (t: (k: string) => string): Record<string, string> => ({
  original_filename: t('col_file') || 'Archivo',
  status: t('col_status') || 'Estado',
  doc_type: t('col_type') || 'Tipo',
  lang: t('col_lang') || 'Idioma',
  page_count: t('col_pages') || 'Páginas',
  size_bytes: t('col_size') || 'Tamaño',
  processing_ms: t('col_latency') || 'Latencia',
  created_at: t('col_created') || 'Creado',
})

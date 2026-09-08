import type { DocExtraction } from '@/services/ocr-api'

const FIELD_LABEL: Record<string, string> = {
  total: 'Total',
  net_pay: 'Líquido a percibir',
  gross_pay: 'Total devengado',
  date: 'Fecha',
  period: 'Período',
  tax_id: 'CIF / NIF',
  invoice_number: 'Nº factura',
  order_number: 'Nº pedido',
  iban: 'IBAN',
  closing_balance: 'Saldo final',
  document_number: 'Nº documento',
  birth_date: 'Fecha de nacimiento',
  email: 'Email',
  phone: 'Teléfono',
}

/** Key/value table of the fields the extractor pulled out of a document. */
export function ExtractionFields({ extraction }: { extraction: DocExtraction | null | undefined }) {
  const entries = Object.entries(extraction?.fields ?? {})
  if (entries.length === 0) return null

  return (
    <div className="rounded-md border">
      <p className="border-b bg-muted/50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Campos extraídos
      </p>
      <dl className="divide-y text-sm">
        {entries.map(([key, field]) => (
          <div key={key} className="flex items-center justify-between gap-4 px-3 py-1.5">
            <dt className="text-muted-foreground">{FIELD_LABEL[key] ?? key}</dt>
            <dd className="font-medium tabular-nums">{field.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

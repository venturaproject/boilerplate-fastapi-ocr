import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Eye } from 'lucide-react'
import { useI18n } from '@/i18n/context'

interface DeliveryReceipt {
  id: number
  device_id: number
  employee_synergy_res_id: number | null
  user_id: number | null
  signature_path: string | null
  pdf_path: string | null
  email_sent_to: string | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
  employee?: { nombre_completo: string; email: string | null } | null
  user?: { name: string } | null
}

interface DeliveryReceiptsTableProps {
  receipts: DeliveryReceipt[]
}

export function DeliveryReceiptsTable({ receipts = [] }: DeliveryReceiptsTableProps) {
  const { t } = useI18n()

  if (receipts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5" />
            Acuses de Entrega
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Sin acuses de entrega registrados</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="h-5 w-5" />
          Acuses de Entrega
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha de Entrega</TableHead>
              <TableHead>Empleado</TableHead>
              <TableHead>Usuario de Entrega</TableHead>
              <TableHead>Email Enviado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {receipts.map((receipt) => (
              <TableRow key={receipt.id}>
                <TableCell className="text-sm">
                  {new Date(receipt.created_at).toLocaleDateString('es-ES', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </TableCell>
                <TableCell className="text-sm">
                  {receipt.employee?.nombre_completo || '-'}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {receipt.user?.name || '-'}
                </TableCell>
                <TableCell className="text-sm">
                  {receipt.email_sent_to ? (
                    <span className="text-green-600">✓ {receipt.email_sent_to}</span>
                  ) : (
                    <span className="text-muted-foreground">No enviado</span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {receipt.pdf_path && (
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                    >
                      <a
                        href={`/device-receipts/${receipt.id}/pdf`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Eye className="mr-1 h-4 w-4" />
                        Ver PDF
                      </a>
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

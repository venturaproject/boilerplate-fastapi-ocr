import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Phone } from 'lucide-react'
import { useI18n } from '@/i18n/context'

interface Props {
  phones: {
    id: number
    telefono: string
    estado_telefonos_id: number
    status_nombre: string
    nplan: string
    trabajador_nombre: string | null
    activo: boolean
    fecha_cese: string | null
  }[]
}

const statusColors: Record<number, string> = {
  1: 'bg-green-100 text-green-700 border-green-200',
  2: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  3: 'bg-red-100 text-red-700 border-red-200',
  5: 'bg-gray-100 text-gray-700 border-gray-200',
}

export function DevicePhonesTable({ phones = [] }: Props) {
  const { t } = useI18n()
  const [showCese, setShowCese] = useState(false)

  if (phones.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Phone className="h-5 w-5" />
            Teléfonos Asociados
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Sin teléfonos asociados a este dispositivo</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Phone className="h-5 w-5" />
            Teléfonos Asociados
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCese(!showCese)}
          >
            {showCese ? 'Ocultar' : 'Mostrar'} Fecha de Cese
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Teléfono</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Trabajador</TableHead>
              {showCese && <TableHead className="text-right">Fecha de Cese</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {phones.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-mono">{p.telefono}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={statusColors[p.estado_telefonos_id] || ''}>
                    {p.status_nombre}
                  </Badge>
                </TableCell>
                <TableCell>{p.nplan || '-'}</TableCell>
                <TableCell>
                  <div className="flex flex-col">
                    <span>{p.trabajador_nombre || '-'}</span>
                    {!p.activo && p.trabajador_nombre && (
                      <span className="text-xs text-muted-foreground">Inactivo</span>
                    )}
                  </div>
                </TableCell>
                {showCese && (
                  <TableCell className="text-right">
                    {p.fecha_cese
                      ? new Date(p.fecha_cese).toLocaleDateString('es-ES', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                        })
                      : p.activo
                      ? <Badge variant="secondary" className="bg-green-100 text-green-700">Activo</Badge>
                      : '-'}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

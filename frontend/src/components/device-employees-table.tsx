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
import { Users } from 'lucide-react'
import { useI18n } from '@/i18n/context'

interface Props {
  employees: {
    id: number
    nombre_completo: string
    email: string | null
    ubicacion: string | null
    telefono: string | null
    telefono_synergy: string | null
    activo: boolean
    fecha_cese: string | null
  }[]
}

export function DeviceEmployeesTable({ employees = [] }: Props) {
  const { t } = useI18n()

  if (employees.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-5 w-5" />
            Trabajadores Asociados
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Sin trabajadores asociados a este dispositivo</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-5 w-5" />
          Trabajadores Asociados
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Ubicación</TableHead>
              <TableHead>Teléfono</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {employees.map((emp) => (
              <TableRow key={emp.id}>
                <TableCell className="font-medium">{emp.nombre_completo}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{emp.ubicacion || '-'}</TableCell>
                <TableCell className="font-mono text-sm">
                  {emp.telefono || emp.telefono_synergy || '-'}
                </TableCell>
                <TableCell>
                  {emp.activo ? (
                    <Badge variant="secondary" className="bg-green-100 text-green-700">Activo</Badge>
                  ) : emp.fecha_cese ? (
                    <Badge variant="secondary" className="bg-red-100 text-red-700">
                      Baja: {new Date(emp.fecha_cese).toLocaleDateString('es-ES')}
                    </Badge>
                  ) : (
                    <Badge variant="secondary">Inactivo</Badge>
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

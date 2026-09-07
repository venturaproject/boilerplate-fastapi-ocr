import { createColumnHelper } from '@tanstack/react-table'
import { MoreHorizontal, Eye, Pencil } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { pathFor } from '@/lib/app-routes'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Dispositivo } from './types'

const columnHelper = createColumnHelper<Dispositivo>()

interface BuildColumnsOptions {
  t: (key: string, params?: Record<string, string | number>) => string
  selectedIds: Set<number>
  allPageSelected: boolean
  toggleSelectAll: (checked: boolean) => void
  toggleSelectRow: (id: number, checked: boolean) => void
  phoneMap: Record<string, number>
}

export function buildDispositivosColumns({
  t,
  selectedIds,
  allPageSelected,
  toggleSelectAll,
  toggleSelectRow,
  phoneMap,
}: BuildColumnsOptions) {
  return [
    columnHelper.display({
      id: 'select',
      enableHiding: false,
      header: () => (
        <Checkbox
          checked={allPageSelected}
          onCheckedChange={(checked) => toggleSelectAll(!!checked)}
          aria-label={t('select_all')}
        />
      ),
      cell: (info) => (
        <Checkbox
          checked={selectedIds.has(info.row.original.id)}
          onCheckedChange={(checked) => toggleSelectRow(info.row.original.id, !!checked)}
          aria-label={t('select_row')}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    }),
    columnHelper.accessor('marca', {
      id: 'marca',
      header: () => t('col_marca'),
      cell: (info) => <span className="text-sm">{info.getValue() || '-'}</span>,
    }),
    columnHelper.accessor('modelo', {
      id: 'modelo',
      header: () => t('col_modelo'),
      cell: (info) => <span className="text-sm">{info.getValue() || '-'}</span>,
    }),
    columnHelper.accessor('imei', {
      id: 'imei',
      header: () => t('col_imei'),
      cell: (info) => (
        <span className="font-mono text-sm">{info.getValue() || '-'}</span>
      ),
    }),
    columnHelper.accessor('numero', {
      id: 'numero',
      header: () => t('col_telefono'),
      cell: (info) => {
        const numero = info.getValue()
        const phoneId = numero ? phoneMap[numero] : undefined

        if (!numero) {
          return <span className="font-mono text-sm text-muted-foreground">-</span>
        }

        if (phoneId) {
          return (
            <Link
              to={pathFor('admin.telefonos.show', phoneId)}
              className="font-mono text-sm text-primary hover:underline"
            >
              {numero}
            </Link>
          )
        }

        return <span className="font-mono text-sm text-muted-foreground">{numero}</span>
      },
    }),
    columnHelper.accessor('grupo', {
      id: 'grupo',
      header: () => t('col_grupo'),
      cell: (info) => {
        const grupo = info.getValue()
        return grupo ? (
          <Badge variant="secondary">{grupo}</Badge>
        ) : (
          <span className="text-sm text-muted-foreground">-</span>
        )
      },
    }),
    columnHelper.accessor('employee', {
      id: 'employee',
      header: () => t('col_trabajador'),
      cell: (info) => {
        const emp = info.getValue()
        return emp ? (
          <span className="text-sm">{emp.nombre_completo}</span>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        )
      },
    }),
    columnHelper.display({
      id: 'actions',
      enableHiding: false,
      header: () => <span className="sr-only">{t('actions')}</span>,
      cell: (info) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button aria-haspopup="true" size="icon" variant="ghost">
              <MoreHorizontal className="h-4 w-4" />
              <span className="sr-only">{t('actions')}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{t('actions')}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to={pathFor('admin.dispositivos.show', info.row.original.id)}>
                <Eye className="mr-2 h-4 w-4" />
                {t('action_ver')}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to={pathFor('admin.dispositivos.edit', info.row.original.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Editar
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    }),
  ]
}

export const dispositivoColumnLabels = (t: (k: string) => string): Record<string, string> => ({
  marca: t('col_marca'),
  modelo: t('col_modelo'),
  imei: t('col_imei'),
  numero: t('col_telefono'),
  grupo: t('col_grupo'),
  employee: t('col_trabajador'),
})

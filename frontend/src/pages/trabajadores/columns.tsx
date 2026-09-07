import { createColumnHelper } from '@tanstack/react-table'
import { MoreHorizontal, Eye } from 'lucide-react'
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
import { Trabajador, formatDate } from './types'

const columnHelper = createColumnHelper<Trabajador>()

interface BuildColumnsOptions {
  t: (key: string, params?: Record<string, string | number>) => string
  selectedIds: Set<number>
  allPageSelected: boolean
  toggleSelectAll: (checked: boolean) => void
  toggleSelectRow: (id: number, checked: boolean) => void
  phoneMap: Record<string, number>
}

export function buildTrabajadoresColumns({
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
    columnHelper.accessor('synergy_res_id', {
      id: 'synergy_res_id',
      header: () => t('col_res_id'),
      cell: (info) => {
        const val = info.getValue()
        return <span className="font-mono text-sm">{val ?? '-'}</span>
      },
    }),
    columnHelper.accessor('nombre_completo', {
      id: 'nombre_completo',
      header: () => t('col_nombre'),
      cell: (info) => <span className="font-medium">{info.getValue()}</span>,
    }),
    columnHelper.accessor('email', {
      id: 'email',
      header: () => t('col_email'),
      cell: (info) => (
        <span className="text-sm text-muted-foreground">{info.getValue() ?? '-'}</span>
      ),
    }),
    columnHelper.accessor('ubicacion', {
      id: 'ubicacion',
      header: () => t('col_ubicacion'),
      cell: (info) => <span className="text-sm">{info.getValue()?.trim() ?? '-'}</span>,
    }),
    columnHelper.accessor('ciudad', {
      id: 'ciudad',
      header: () => t('col_ciudad'),
      cell: (info) => <span className="text-sm">{info.getValue() ?? '-'}</span>,
    }),
    columnHelper.accessor('telefono_synergy', {
      id: 'telefono_synergy',
      header: () => t('col_telefono'),
      cell: (info) => {
        const telefono = info.getValue()
        const phoneId = telefono ? phoneMap[telefono] : undefined

        if (!telefono) {
          return <span className="font-mono text-sm text-muted-foreground">-</span>
        }

        if (phoneId) {
          return (
            <Link
              to={pathFor('admin.telefonos.show', phoneId)}
              className="font-mono text-sm text-primary hover:underline"
            >
              {telefono}
            </Link>
          )
        }

        return <span className="font-mono text-sm text-muted-foreground">{telefono}</span>
      },
    }),
    columnHelper.accessor('imei', {
      id: 'imei',
      header: () => t('col_imei'),
      cell: (info) => <span className="font-mono text-sm">{info.getValue() ?? '-'}</span>,
    }),
    columnHelper.accessor('activo', {
      id: 'activo',
      header: () => t('col_estado'),
      cell: (info) => (
        <Badge variant={info.getValue() ? 'default' : 'secondary'}>
          {info.getValue() ? t('tab_activos') : t('tab_bajas')}
        </Badge>
      ),
    }),
    columnHelper.accessor('fecha_alta', {
      id: 'fecha_alta',
      header: () => t('col_fecha_alta'),
      cell: (info) => formatDate(info.getValue()),
    }),
    columnHelper.display({
      id: 'actions',
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
              <Link to={pathFor('admin.trabajadores.show', info.row.original.id)}>
                <Eye className="mr-2 h-4 w-4" />
                {t('view_detail')}
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    }),
  ]
}

export const trabajadorColumnLabels = (t: (k: string) => string): Record<string, string> => ({
  synergy_res_id: t('col_res_id'),
  nombre_completo: t('col_nombre'),
  email: t('col_email'),
  ubicacion: t('col_ubicacion'),
  ciudad: t('col_ciudad'),
  telefono_synergy: t('col_telefono'),
  imei: t('col_imei'),
  activo: t('col_estado'),
  fecha_alta: t('col_fecha_alta'),
})

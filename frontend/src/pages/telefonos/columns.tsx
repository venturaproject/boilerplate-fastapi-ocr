import { createColumnHelper } from '@tanstack/react-table'
import { MoreHorizontal, Eye, Pencil, PhoneOff, ShieldCheck, ShieldOff, Phone, Snowflake, PhoneCall, CircleDashed, SignalZero } from 'lucide-react'
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { Telefono, statusBadgeClass } from './types'

const columnHelper = createColumnHelper<Telefono>()

interface BuildColumnsOptions {
  t: (key: string, params?: Record<string, string | number>) => string
  selectedIds: Set<number>
  allPageSelected: boolean
  toggleSelectAll: (checked: boolean) => void
  toggleSelectRow: (id: number, checked: boolean) => void
  onDesactivar: (id: number, telefono: string) => void
}

export function buildTelefonosColumns({
  t,
  selectedIds,
  allPageSelected,
  toggleSelectAll,
  toggleSelectRow,
  onDesactivar,
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
    columnHelper.accessor('telefono', {
      id: 'telefono',
      header: () => t('col_telefono'),
      cell: (info) => <span className="font-mono font-medium">{info.getValue()}</span>,
    }),
    columnHelper.accessor('plan', {
      id: 'plan',
      header: () => t('col_plan'),
      cell: (info) => <span className="text-sm">{info.getValue() || '-'}</span>,
    }),
    columnHelper.accessor('estado_telefonos_id', {
      id: 'estado_telefonos_id',
      header: () => t('col_estado'),
      cell: (info) => {
        const estadoId = info.getValue()
        const nombre = info.row.original.status?.nombre ?? String(estadoId)
        
        const statusIcons: Record<number, React.ReactNode> = {
          1: <Phone className="h-3 w-3" />,
          2: <Snowflake className="h-3 w-3" />,
          3: <PhoneOff className="h-3 w-3" />,
          5: <CircleDashed className="h-3 w-3" />,
        }
        
        return (
          <Badge className={cn('gap-1.5', statusBadgeClass(estadoId))}>
            {statusIcons[estadoId] || <Phone className="h-3 w-3" />}
            {nombre}
          </Badge>
        )
      },
    }),
    columnHelper.display({
      id: 'pin_puk',
      header: () => t('col_pin_puk'),
      cell: (info) => {
        const hasCodes = !!(info.row.original.pin && info.row.original.puk)
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex cursor-default items-center gap-1">
                {hasCodes
                  ? <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  : <ShieldOff className="h-4 w-4 text-muted-foreground" />
                }
              </span>
            </TooltipTrigger>
            <TooltipContent>
              {hasCodes ? t('badge_has_codes') : t('badge_no_codes')}
            </TooltipContent>
          </Tooltip>
        )
      },
    }),
    columnHelper.accessor('trabajador', {
      id: 'trabajador',
      header: () => t('col_trabajador'),
      cell: (info) => {
        const trab = info.getValue()
        return trab ? (
          <span className="text-sm">{trab.nombre_completo}</span>
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
              <Link to={pathFor('admin.telefonos.show', info.row.original.id)}>
                <Eye className="mr-2 h-4 w-4" />
                {t('view_detail')}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to={pathFor('admin.telefonos.edit', info.row.original.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Editar
              </Link>
            </DropdownMenuItem>
            {info.row.original.estado_telefonos_id !== 3 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={(e) => {
                    e.preventDefault()
                    onDesactivar(info.row.original.id, info.row.original.telefono)
                  }}
                >
                  <PhoneOff className="mr-2 h-4 w-4" />
                  {t('action_desactivar')}
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    }),
  ]
}

export const telefonoColumnLabels = (t: (k: string) => string): Record<string, string> => ({
  telefono: t('col_telefono'),
  plan: t('col_plan'),
  estado_telefonos_id: t('col_estado'),
  trabajador: t('col_trabajador'),
})

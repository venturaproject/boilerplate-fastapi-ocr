import { useState } from 'react'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { X, Download, CalendarRange, UserCheck, UserX, UserPlus, Building2, Car, Phone, Smartphone } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { useI18n } from '@/i18n/context'
import { PageProps } from '@/types'
import { getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { format } from 'date-fns'
import { DateRange } from 'react-day-picker'
import {
  DataTable,
  DataTablePagination,
  DataTableViewOptions,
  BulkSelectionBar,
} from '@/components/data-table'
import { useTableFilters } from '@/hooks/use-table-filters'
import { useBulkSelection } from '@/hooks/use-bulk-selection'
import { useColumnReorder } from '@/hooks/use-column-reorder'
import { usePhoneLookup } from '@/hooks/use-phone-lookup'
import { submitBulkActionForm } from '@/lib/submit-bulk-action-form'
import { pathFor } from '@/lib/app-routes'
import { buildTrabajadoresColumns, trabajadorColumnLabels } from './columns'
import { AdvancedFilters } from './components/advanced-filters'
import { Trabajador, TrabajadorStats, TrabajadorFilters, FilterOptions } from './types'

const workerStatSeries = {
  activos: [6, 8, 7, 10, 8, 11, 9, 12],
  conTelefono: [5, 7, 6, 8, 7, 10, 8, 11],
  incorporadosEsteMes: [4, 6, 5, 8, 6, 9, 7, 10],
  conImei: [3, 5, 6, 7, 5, 8, 9, 8],
}

interface TrabajadoresPageProps extends PageProps {
  trabajadores?: {
    data: Trabajador[]
    current_page: number
    last_page: number
    per_page: number
    total: number
  }
  filters?: TrabajadorFilters
  filterOptions?: FilterOptions
  stats?: TrabajadorStats
}

export default function Trabajadores({
  trabajadores = { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 },
  filters: initialFilters = {},
  filterOptions = { ubicaciones: [], ciudades: [] },
  stats = { activos: 0, conTelefono: 0, incorporadosEsteMes: 0, conImei: 0 },
}: TrabajadoresPageProps) {
  const { t } = useI18n()

  const [localDateRange, setLocalDateRange] = useState<DateRange | undefined>(
    initialFilters?.date_from
      ? {
          from: new Date(initialFilters.date_from),
          to: initialFilters.date_to ? new Date(initialFilters.date_to) : undefined,
        }
      : undefined
  )

  const pageIds = trabajadores.data.map((w) => w.id)

  const bulk = useBulkSelection(pageIds, trabajadores.total)

  const { filters, searchTerm, navigate, handleSearch, handlePageChange, handlePerPageChange, perPage } =
    useTableFilters<TrabajadorFilters>({
      basePath: pathFor('admin.trabajadores.index'),
      initialFilters: initialFilters ?? {},
      initialPerPage: trabajadores.per_page ?? 20,
      onNavigate: bulk.clearSelection,
    })

  const handleFilterChange = (partial: Partial<TrabajadorFilters>) => {
    navigate({ ...filters, ...partial })
  }

  const handleTabChange = (value: string) => {
    const newFilters = { ...filters }
    if (value === 'activos') newFilters.activo = '1'
    else if (value === 'bajas') newFilters.activo = '0'
    else delete newFilters.activo
    navigate(newFilters)
  }

  const handleCalendarSelect = (range: DateRange | undefined) => {
    setLocalDateRange(range)
    handleFilterChange({
      date_from: range?.from ? format(range.from, 'yyyy-MM-dd') : undefined,
      date_to: range?.to ? format(range.to, 'yyyy-MM-dd') : undefined,
    })
  }

  const applyDatePreset = (from: Date, to: Date) => {
    setLocalDateRange({ from, to })
    handleFilterChange({
      date_from: format(from, 'yyyy-MM-dd'),
      date_to: format(to, 'yyyy-MM-dd'),
    })
  }

  const clearAllFilters = () => {
    setLocalDateRange(undefined)
    navigate({ activo: filters.activo })
  }

  const hasActiveFilters = !!(
    filters.ubicacion || filters.ciudad || filters.search || filters.date_from || filters.date_to
  )

  const phoneNumbers = trabajadores.data
    .map((w) => w.telefono_synergy)
    .filter((n): n is string => !!n)
  const phoneMap = usePhoneLookup(phoneNumbers)

  const columns = buildTrabajadoresColumns({
    t,
    selectedIds: bulk.selectedIds,
    allPageSelected: bulk.allPageSelected,
    toggleSelectAll: bulk.toggleSelectAll,
    toggleSelectRow: bulk.toggleSelectRow,
    phoneMap,
  })

  const { columnOrder, columnVisibility, setColumnVisibility, handleDragStart, handleDrop } =
    useColumnReorder(columns.map((c) => c.id as string))

  const table = useReactTable({
    data: trabajadores.data,
    columns,
    state: { columnOrder, columnVisibility },
    onColumnOrderChange: () => {},
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const currentTab =
    filters.activo === '1' ? 'activos' : filters.activo === '0' ? 'bajas' : 'all'

  const countLabel = bulk.selectAllRecords
    ? t('trabajadores_selected_all', { total: trabajadores.total })
    : `${bulk.selectedCount} ${bulk.selectedCount === 1 ? t('trabajador_selected_one') : t('trabajadores_selected_other')}`

  return (
    <AuthenticatedLayout title={t('trabajadores_title')}>
      <Main>
        <div className="grid flex-1 items-start gap-4 md:gap-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{t('trabajadores_title')}</h2>
            <p className="text-muted-foreground">{t('trabajadores_page_description')}</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricStatCard title={t('stat_activos_title')} value={stats.activos} subtitle={t('stat_en_activo')} icon={UserCheck} tooltip={t('stat_activos_tooltip')} trend={15.5} sparklineColor="#10b981" sparklineData={workerStatSeries.activos} detailsLabel={t('stat_en_activo')} />
            <MetricStatCard title={t('stat_con_telefono_title')} value={stats.conTelefono} subtitle={t('stat_con_telefono_subtitle')} icon={Phone} tooltip={t('stat_con_telefono_tooltip')} trend={10.8} sparklineColor="#6366f1" sparklineData={workerStatSeries.conTelefono} detailsLabel={t('stat_con_telefono_label')} />
            <MetricStatCard title={t('stat_incorporados_este_mes')} value={stats.incorporadosEsteMes} subtitle={t('stat_incorporaciones')} icon={UserPlus} tooltip={t('stat_altas_tooltip')} trend={8.4} sparklineColor="#f59e0b" sparklineData={workerStatSeries.incorporadosEsteMes} detailsLabel={t('stat_este_mes')} />
            <MetricStatCard title={t('stat_con_imei_title')} value={stats.conImei} subtitle={t('stat_con_imei_subtitle')} icon={Smartphone} tooltip={t('stat_con_imei_tooltip')} trend={6.2} sparklineColor="#8b5cf6" sparklineData={workerStatSeries.conImei} detailsLabel={t('stat_con_imei_label')} />
          </div>

          <Tabs value={currentTab} onValueChange={handleTabChange}>
            <div className="flex items-center">
              <TabsList>
                <TabsTrigger value="all">{t('tab_todos')}</TabsTrigger>
                <TabsTrigger value="activos">{t('tab_activos')}</TabsTrigger>
                <TabsTrigger value="bajas">{t('tab_bajas')}</TabsTrigger>
              </TabsList>
              <div className="ml-auto flex items-center gap-2">
                <div className="relative">
                  <Input
                    placeholder={t('search_trabajadores')}
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-72 pr-9"
                  />
                  {searchTerm && (
                    <Button type="button" variant="ghost" size="icon" className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground" onClick={() => handleSearch('')}>
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <DataTableViewOptions table={table} columnLabels={trabajadorColumnLabels(t)} />
                <AdvancedFilters
                  filters={filters}
                  filterOptions={filterOptions}
                  localDateRange={localDateRange}
                  hasActiveFilters={hasActiveFilters}
                  onFilterChange={handleFilterChange}
                  onCalendarSelect={handleCalendarSelect}
                  onApplyDatePreset={applyDatePreset}
                  onClearAll={clearAllFilters}
                />
              </div>
            </div>

            <BulkSelectionBar
              visible={bulk.selectedIds.size > 0}
              selectedCount={bulk.selectedCount}
              total={trabajadores.total}
              allPageSelected={bulk.allPageSelected}
              selectAllRecords={bulk.selectAllRecords}
              onSelectAllRecords={() => bulk.setSelectAllRecords(true)}
              onSelectPageOnly={() => bulk.setSelectAllRecords(false)}
              onClearSelection={bulk.clearSelection}
              countLabel={countLabel}
              selectAllLabel={t('select_all_trabajadores', { total: trabajadores.total })}
              actions={
                <DropdownMenuItem
                  onClick={() =>
                    submitBulkActionForm(pathFor('admin.trabajadores.bulk-export'), bulk.selectedIds, bulk.selectAllRecords, filters)
                  }
                >
                  <Download className="mr-2 h-4 w-4" />
                  {t('export_excel')}
                </DropdownMenuItem>
              }
            />

            {(filters.date_from || filters.date_to) && (
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="secondary" className="gap-1">
                  <CalendarRange className="h-3 w-3" />
                  {filters.date_from && filters.date_to
                    ? `${format(new Date(filters.date_from), 'dd/MM/yy')} – ${format(new Date(filters.date_to), 'dd/MM/yy')}`
                    : filters.date_from
                    ? t('from_date', { date: format(new Date(filters.date_from), 'dd/MM/yy') })
                    : t('to_date', { date: format(new Date(filters.date_to!), 'dd/MM/yy') })}
                  <button
                    onClick={() => {
                      setLocalDateRange(undefined)
                      handleFilterChange({ date_from: undefined, date_to: undefined })
                    }}
                    className="ml-1 hover:bg-secondary-foreground/20 rounded-full"
                  >
                    ×
                  </button>
                </Badge>
              </div>
            )}

            <TabsContent value={currentTab}>
              <Card>
                <CardHeader>
                  <CardTitle>{t('all_trabajadores_title')}</CardTitle>
                  <CardDescription>{t('all_trabajadores_description')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <DataTable
                    table={table}
                    colCount={columns.length}
                    emptyMessage={t('no_trabajadores_found')}
                    onDragStart={handleDragStart}
                    onDrop={handleDrop}
                  />
                </CardContent>
                <DataTablePagination
                  currentPage={trabajadores.current_page}
                  lastPage={trabajadores.last_page}
                  perPage={perPage}
                  total={trabajadores.total}
                  selectedCount={bulk.selectedCount}
                  onPageChange={handlePageChange}
                  onPerPageChange={handlePerPageChange}
                />
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

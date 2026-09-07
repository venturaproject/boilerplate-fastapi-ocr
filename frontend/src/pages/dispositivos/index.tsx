import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { X, Cpu, Smartphone, UserCheck, UserX, Plus, Download } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { useI18n } from '@/i18n/context'
import { useNavigate } from 'react-router-dom'
import { getCoreRowModel, useReactTable } from '@tanstack/react-table'
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
import { PageProps } from '@/types'
import { buildDispositivosColumns, dispositivoColumnLabels } from './columns'
import { DeviceFilters } from './components/device-filters'
import { Dispositivo, DispositivoStats, DispositivoFilters, DeviceFilterOptions } from './types'

const DEVICE_TYPES = [
  { value: 'Teléfonos', labelKey: 'tab_telefonos' },
  { value: 'Tabletas', labelKey: 'tab_tabletas' },
  { value: 'Bases Wifi', labelKey: 'tab_bases_wifi' },
] as const

const deviceStatSeries = {
  total: [5, 6, 7, 8, 9, 10, 11, 12],
  withImei: [4, 5, 6, 7, 8, 9, 10, 11],
  assigned: [2, 3, 3, 4, 5, 5, 6, 7],
  unassigned: [3, 3, 4, 4, 4, 5, 5, 5],
}

interface DispositivosPageProps extends PageProps {
  dispositivos?: {
    data: Dispositivo[]
    current_page: number
    last_page: number
    per_page: number
    total: number
  }
  filters?: DispositivoFilters
  filterOptions?: DeviceFilterOptions
  stats?: DispositivoStats
}

export default function Dispositivos({
  dispositivos = { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 },
  filters: initialFilters = {},
  filterOptions = { marcas: [], tipos: [] },
  stats = { total: 0, withImei: 0, withNumero: 0, assigned: 0, unassigned: 0 },
}: DispositivosPageProps) {
  const { t } = useI18n()
  const navigateTo = useNavigate()

  const pageIds = dispositivos.data.map((d) => d.id)

  const bulk = useBulkSelection(pageIds, dispositivos.total)

  const { filters, searchTerm, navigate, handleSearch, handlePageChange, handlePerPageChange, perPage } =
    useTableFilters<DispositivoFilters>({
      basePath: pathFor('admin.dispositivos.index'),
      initialFilters: initialFilters ?? {},
      initialPerPage: dispositivos.per_page ?? 20,
      onNavigate: bulk.clearSelection,
    })

  const handleFilterChange = (partial: Partial<DispositivoFilters>) => {
    navigate({ ...filters, ...partial })
  }

  const handleTabChange = (value: string) => {
    const newFilters = { ...filters }
    if (value === 'todos') {
      delete newFilters.grupo
    } else {
      newFilters.grupo = value
    }
    navigate(newFilters)
  }

  const phoneNumbers = dispositivos.data.map((d) => d.numero).filter((n): n is string => !!n)
  const phoneMap = usePhoneLookup(phoneNumbers)

  const columns = buildDispositivosColumns({
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
    data: dispositivos.data,
    columns,
    state: { columnOrder, columnVisibility },
    onColumnOrderChange: () => {},
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const currentTab = filters.grupo ?? 'todos'

  const hasActiveFilters = !!(filters.marca || filters.tipo)

  const clearAllFilters = () => {
    navigate({ grupo: filters.grupo })
  }

  const countLabel = bulk.selectAllRecords
    ? t('dispositivos_selected_all', { total: dispositivos.total })
    : `${bulk.selectedCount} ${bulk.selectedCount === 1 ? t('dispositivo_selected_one') : t('dispositivos_selected_other')}`

  return (
    <AuthenticatedLayout title={t('dispositivos_title')}>
      <Main>
        <div className="grid flex-1 items-start gap-4 md:gap-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">{t('dispositivos_title')}</h2>
              <p className="text-muted-foreground">{t('dispositivos_page_description')}</p>
            </div>
            <Button onClick={() => navigateTo(pathFor('admin.dispositivos.create'))}>
              <Plus className="mr-2 h-4 w-4" />
              {t('create_device')}
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricStatCard
              title={t('stat_total_dispositivos_title')}
              value={stats.total}
              subtitle={t('stat_total_dispositivos_subtitle')}
              icon={Cpu}
              trend={15.2}
              sparklineColor="#6366f1"
              sparklineData={deviceStatSeries.total}
              detailsLabel={t('stat_total_dispositivos_subtitle')}
            />
            <MetricStatCard
              title={t('stat_con_imei_title')}
              value={stats.withImei}
              subtitle={t('stat_con_imei_subtitle')}
              icon={Smartphone}
              trend={8.4}
              sparklineColor="#10b981"
              sparklineData={deviceStatSeries.withImei}
              detailsLabel={t('stat_con_imei_subtitle')}
            />
            <MetricStatCard
              title={t('stat_asignados_title')}
              value={stats.assigned}
              subtitle={t('stat_asignados_subtitle')}
              icon={UserCheck}
              trend={11.3}
              sparklineColor="#60a5fa"
              sparklineData={deviceStatSeries.assigned}
              detailsLabel={t('stat_asignados_subtitle')}
            />
            <MetricStatCard
              title={t('stat_sin_asignar_title')}
              value={stats.unassigned}
              subtitle={t('stat_sin_asignar_subtitle')}
              icon={UserX}
              trend={-2.1}
              sparklineColor="#f87171"
              sparklineData={deviceStatSeries.unassigned}
              detailsLabel={t('stat_sin_asignar_subtitle')}
            />
          </div>

          <Tabs value={currentTab} onValueChange={handleTabChange}>
            <div className="flex items-center">
              <TabsList>
                <TabsTrigger value="todos">{t('tab_todos')}</TabsTrigger>
                {DEVICE_TYPES.map((dt) => (
                  <TabsTrigger key={dt.value} value={dt.value}>
                    {t(dt.labelKey)}
                  </TabsTrigger>
                ))}
              </TabsList>
              <div className="ml-auto flex items-center gap-2">
                <div className="relative">
                  <Input
                    placeholder={t('search_dispositivos')}
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-72 pr-9"
                  />
                  {searchTerm && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground"
                      onClick={() => handleSearch('')}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <DataTableViewOptions table={table} columnLabels={dispositivoColumnLabels(t)} />
                <DeviceFilters
                  filters={filters}
                  filterOptions={filterOptions}
                  hasActiveFilters={hasActiveFilters}
                  onFilterChange={handleFilterChange}
                  onClearAll={clearAllFilters}
                />
              </div>
            </div>

            <BulkSelectionBar
              visible={bulk.selectedIds.size > 0}
              selectedCount={bulk.selectedCount}
              total={dispositivos.total}
              allPageSelected={bulk.allPageSelected}
              selectAllRecords={bulk.selectAllRecords}
              onSelectAllRecords={() => bulk.setSelectAllRecords(true)}
              onSelectPageOnly={() => bulk.setSelectAllRecords(false)}
              onClearSelection={bulk.clearSelection}
              countLabel={countLabel}
              selectAllLabel={t('select_all_dispositivos', { total: dispositivos.total })}
              actions={
                <>
                  <DropdownMenuItem
                    onClick={() =>
                      submitBulkActionForm(pathFor('admin.dispositivos.bulk-export'), bulk.selectedIds, bulk.selectAllRecords, filters)
                    }
                  >
                    <Download className="mr-2 h-4 w-4" />
                    {t('export_excel')}
                  </DropdownMenuItem>
                </>
              }
            />

            {hasActiveFilters && (
              <div className="flex items-center gap-2 flex-wrap">
                {filters.marca && (
                  <Badge variant="secondary" className="gap-1">
                    {t('col_marca')}: {filters.marca}
                    <button
                      onClick={() => handleFilterChange({ marca: undefined })}
                      className="ml-1 hover:bg-secondary-foreground/20 rounded-full"
                    >
                      ×
                    </button>
                  </Badge>
                )}
                {filters.tipo && (
                  <Badge variant="secondary" className="gap-1">
                    {t('col_tipo')}: {filters.tipo}
                    <button
                      onClick={() => handleFilterChange({ tipo: undefined })}
                      className="ml-1 hover:bg-secondary-foreground/20 rounded-full"
                    >
                      ×
                    </button>
                  </Badge>
                )}
              </div>
            )}

            <TabsContent value={currentTab}>
              <Card>
                <CardHeader>
                  <CardTitle>{t('all_dispositivos_title')}</CardTitle>
                  <CardDescription>{t('all_dispositivos_description')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <DataTable
                    table={table}
                    colCount={columns.length}
                    emptyMessage={t('no_dispositivos_found')}
                    onDragStart={handleDragStart}
                    onDrop={handleDrop}
                  />
                </CardContent>
                <DataTablePagination
                  currentPage={dispositivos.current_page}
                  lastPage={dispositivos.last_page}
                  perPage={perPage}
                  total={dispositivos.total}
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

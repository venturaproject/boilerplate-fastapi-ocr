import { useState } from 'react'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { MetricStatCard } from '@/components/metric-stat-card'
import { X, Download, Phone, PhoneOff, Snowflake, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { useI18n } from '@/i18n/context'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useFlashToast } from '@/hooks/use-flash-toast'
import { PageProps } from '@/types'
import { getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { toast } from 'sonner'
import {
  DataTable,
  DataTablePagination,
  DataTableViewOptions,
  BulkSelectionBar,
} from '@/components/data-table'
import { useTableFilters } from '@/hooks/use-table-filters'
import { useBulkSelection } from '@/hooks/use-bulk-selection'
import { useColumnReorder } from '@/hooks/use-column-reorder'
import { submitBulkActionForm } from '@/lib/submit-bulk-action-form'
import { pathFor } from '@/lib/app-routes'
import { telefonosApi } from '@/services/telefonos-api'
import { buildTelefonosColumns, telefonoColumnLabels } from './columns'
import { PhoneFilters } from './components/phone-filters'
import { Telefono, TelefonoStats, TelefonoFilters, PhoneFilterOptions } from './types'

const phoneStatSeries = {
  total: [8, 9, 7, 10, 8, 11, 9, 12],
  active: [6, 7, 8, 7, 9, 10, 9, 11],
  frozen: [7, 6, 8, 5, 7, 4, 6, 5],
  inactive: [8, 7, 6, 7, 5, 6, 4, 5],
}

interface TelefonosPageProps extends PageProps {
  telefonos?: {
    data: Telefono[]
    current_page: number
    last_page: number
    per_page: number
    total: number
  }
  filters?: TelefonoFilters
  filterOptions?: PhoneFilterOptions
  stats?: TelefonoStats
}

export default function Telefonos({
  telefonos = { data: [], current_page: 1, last_page: 1, per_page: 20, total: 0 },
  filters: initialFilters = {},
  filterOptions = { planes: [] },
  stats = { total: 0, activos: 0, congelados: 0, bajas: 0, sinDatos: 0 },
}: TelefonosPageProps) {
  const { t } = useI18n()
  useFlashToast()

  const [confirmDesactivar, setConfirmDesactivar] = useState<{
    open: boolean
    id: number | null
    telefono: string
  }>({ open: false, id: null, telefono: '' })

  const [confirmBulkDesactivar, setConfirmBulkDesactivar] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  const handleSync = () => {
    setIsSyncing(true)
    telefonosApi.sync()
      .catch(() => toast.error(t('please_try_again')))
      .finally(() => setIsSyncing(false))
  }

  const confirmBulkDesactivarLineas = () => {
    const count = bulk.selectedCount
    const ids = Array.from(bulk.selectedIds)
    const selectAll = bulk.selectAllRecords

    setConfirmBulkDesactivar(false)

    const data = selectAll
      ? { select_all: 1, filters }
      : { ids }

    telefonosApi.bulkDesactivar(data)
      .then(() => {
        bulk.clearSelection()
        toast.warning(t('lines_deactivated', { count }))
      })
      .catch(() => toast.error(t('please_try_again')))
  }

  const pageIds = telefonos.data.map((t) => t.id)

  const bulk = useBulkSelection(pageIds, telefonos.total)

  const { filters, searchTerm, navigate, handleSearch, handlePageChange, handlePerPageChange, perPage } =
    useTableFilters<TelefonoFilters>({
      basePath: pathFor('admin.telefonos.index'),
      initialFilters: initialFilters ?? {},
      initialPerPage: telefonos.per_page ?? 20,
      onNavigate: bulk.clearSelection,
    })

  const handleTabChange = (value: string) => {
    const newFilters = { ...filters }
    if (value === 'activos') newFilters.status = '1'
    else if (value === 'congelados') newFilters.status = '2'
    else if (value === 'bajas') newFilters.status = '3'
    else if (value === 'sin_datos') newFilters.status = '5'
    else delete newFilters.status
    navigate(newFilters)
  }

  const handleFilterChange = (partial: Partial<TelefonoFilters>) => {
    navigate({ ...filters, ...partial })
  }

  const hasActiveFilters = !!filters.plan

  const clearAllFilters = () => {
    navigate({ status: filters.status })
  }

  const handleDesactivar = (id: number, telefono: string) => {
    setConfirmDesactivar({ open: true, id, telefono })
  }

  const confirmDesactivarLinea = () => {
    if (!confirmDesactivar.id) return
    const { id, telefono } = confirmDesactivar
    setConfirmDesactivar({ open: false, id: null, telefono: '' })
    telefonosApi.desactivar(id)
      .then(() => toast.warning(`${t('line_deactivated')}: ${telefono}`))
      .catch(() => toast.error(t('please_try_again')))
  }

  const columns = buildTelefonosColumns({
    t,
    selectedIds: bulk.selectedIds,
    allPageSelected: bulk.allPageSelected,
    toggleSelectAll: bulk.toggleSelectAll,
    toggleSelectRow: bulk.toggleSelectRow,
    onDesactivar: handleDesactivar,
  })

  const { columnOrder, columnVisibility, setColumnVisibility, handleDragStart, handleDrop } =
    useColumnReorder(columns.map((c) => c.id as string))

  const table = useReactTable({
    data: telefonos.data,
    columns,
    state: { columnOrder, columnVisibility },
    onColumnOrderChange: () => {},
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  const currentTab =
    filters.status === '1' ? 'activos'
    : filters.status === '2' ? 'congelados'
    : filters.status === '3' ? 'bajas'
    : filters.status === '5' ? 'sin_datos'
    : 'all'

  const countLabel = bulk.selectAllRecords
    ? t('telefonos_selected_all', { total: telefonos.total })
    : `${bulk.selectedCount} ${bulk.selectedCount === 1 ? t('telefono_selected_one') : t('telefonos_selected_other')}`

  return (
    <AuthenticatedLayout title={t('telefonos_title')}>
      <Main>
        <div className="grid flex-1 items-start gap-4 md:gap-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">{t('telefonos_title')}</h2>
              <p className="text-muted-foreground">{t('telefonos_page_description')}</p>
            </div>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={handleSync} disabled={isSyncing} variant="outline">
                    <RefreshCw className={`mr-2 h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
                    {isSyncing ? t('sync_telefonos_loading') : t('sync_telefonos')}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Sincroniza los datos de líneas y planes desde Gored</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricStatCard title={t('stat_total_telefonos_title')} value={stats.total} subtitle={t('stat_total_telefonos_subtitle')} icon={Phone} tooltip={t('stat_total_telefonos_tooltip')} trend={12.6} sparklineColor="#6366f1" sparklineData={phoneStatSeries.total} detailsLabel={t('stat_total_telefonos_subtitle')} />
            <MetricStatCard title={t('stat_telefonos_activos_title')} value={stats.activos} subtitle={t('stat_telefonos_activos_subtitle')} icon={Phone} tooltip={t('stat_telefonos_activos_tooltip')} trend={9.8} sparklineColor="#10b981" sparklineData={phoneStatSeries.active} detailsLabel={t('stat_telefonos_activos_subtitle')} />
            <MetricStatCard title={t('stat_telefonos_congelados_title')} value={stats.congelados} subtitle={t('stat_telefonos_congelados_subtitle')} icon={Snowflake} tooltip={t('stat_telefonos_congelados_tooltip')} trend={-6.4} sparklineColor="#60a5fa" sparklineData={phoneStatSeries.frozen} detailsLabel={t('stat_telefonos_congelados_subtitle')} />
            <MetricStatCard title={t('stat_telefonos_bajas_title')} value={stats.bajas} subtitle={t('stat_telefonos_bajas_subtitle')} icon={PhoneOff} tooltip={t('stat_telefonos_bajas_tooltip')} trend={-4.8} sparklineColor="#f87171" sparklineData={phoneStatSeries.inactive} detailsLabel={t('stat_telefonos_bajas_subtitle')} />
          </div>

          <Tabs value={currentTab} onValueChange={handleTabChange}>
            <div className="flex items-center">
              <TabsList>
                <TabsTrigger value="all">{t('tab_todos')}</TabsTrigger>
                <TabsTrigger value="activos">{t('tab_activos')}</TabsTrigger>
                <TabsTrigger value="congelados">{t('tab_congelados')}</TabsTrigger>
                <TabsTrigger value="bajas">{t('tab_bajas_telefono')}</TabsTrigger>
                <TabsTrigger value="sin_datos">{t('tab_sin_datos')}</TabsTrigger>
              </TabsList>
              <div className="ml-auto flex items-center gap-2">
                <div className="relative">
                  <Input
                    placeholder={t('search_telefonos')}
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
                <DataTableViewOptions table={table} columnLabels={telefonoColumnLabels(t)} />
                <PhoneFilters
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
              total={telefonos.total}
              allPageSelected={bulk.allPageSelected}
              selectAllRecords={bulk.selectAllRecords}
              onSelectAllRecords={() => bulk.setSelectAllRecords(true)}
              onSelectPageOnly={() => bulk.setSelectAllRecords(false)}
              onClearSelection={bulk.clearSelection}
              countLabel={countLabel}
              selectAllLabel={t('select_all_telefonos', { total: telefonos.total })}
              actions={
                <>
                  <DropdownMenuItem
                    onClick={() =>
                      submitBulkActionForm(pathFor('admin.telefonos.bulk-export'), bulk.selectedIds, bulk.selectAllRecords, filters)
                    }
                  >
                    <Download className="mr-2 h-4 w-4" />
                    {t('export_excel')}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => setConfirmBulkDesactivar(true)}
                  >
                    <PhoneOff className="mr-2 h-4 w-4" />
                    {t('action_desactivar')}
                  </DropdownMenuItem>
                </>
              }
            />

            {hasActiveFilters && (
              <div className="flex items-center gap-2 flex-wrap">
                {filters.plan && (
                  <Badge variant="secondary" className="gap-1">
                    {t('col_plan')}: {filters.plan}
                    <button
                      onClick={() => handleFilterChange({ plan: undefined })}
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
                  <CardTitle>{t('all_telefonos_title')}</CardTitle>
                  <CardDescription>{t('all_telefonos_description')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <DataTable
                    table={table}
                    colCount={columns.length}
                    emptyMessage={t('no_telefonos_found')}
                    onDragStart={handleDragStart}
                    onDrop={handleDrop}
                  />
                </CardContent>
                <DataTablePagination
                  currentPage={telefonos.current_page}
                  lastPage={telefonos.last_page}
                  perPage={perPage}
                  total={telefonos.total}
                  selectedCount={bulk.selectedCount}
                  onPageChange={handlePageChange}
                  onPerPageChange={handlePerPageChange}
                />
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </Main>

      <ConfirmDialog
        open={confirmDesactivar.open}
        onOpenChange={(open) => setConfirmDesactivar((s) => ({ ...s, open }))}
        title={t('confirm_desactivar_title')}
        desc={t('confirm_desactivar_desc', { telefono: confirmDesactivar.telefono })}
        destructive
        handleConfirm={confirmDesactivarLinea}
        confirmText={t('action_desactivar')}
        cancelBtnText={t('cancel')}
      />

      <ConfirmDialog
        open={confirmBulkDesactivar}
        onOpenChange={setConfirmBulkDesactivar}
        title={t('confirm_bulk_desactivar_title')}
        desc={t('confirm_bulk_desactivar_desc', { count: bulk.selectedCount })}
        destructive
        handleConfirm={confirmBulkDesactivarLineas}
        confirmText={t('action_desactivar')}
        cancelBtnText={t('cancel')}
      />
    </AuthenticatedLayout>
  )
}

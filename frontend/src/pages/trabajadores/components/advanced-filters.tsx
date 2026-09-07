import { ListFilter, X } from 'lucide-react'
import { format, subDays, startOfWeek, endOfWeek, startOfMonth, endOfMonth, subWeeks, subMonths } from 'date-fns'
import { es } from 'date-fns/locale'
import { DateRange } from 'react-day-picker'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Calendar } from '@/components/ui/calendar'
import { Separator } from '@/components/ui/separator'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useI18n } from '@/i18n/context'
import { FilterOptions, TrabajadorFilters } from '../types'

interface AdvancedFiltersProps {
  filters: TrabajadorFilters
  filterOptions: FilterOptions
  localDateRange: DateRange | undefined
  hasActiveFilters: boolean
  onFilterChange: (partial: Partial<TrabajadorFilters>) => void
  onCalendarSelect: (range: DateRange | undefined) => void
  onApplyDatePreset: (from: Date, to: Date) => void
  onClearAll: () => void
}

export function AdvancedFilters({
  filters,
  filterOptions,
  localDateRange,
  hasActiveFilters,
  onFilterChange,
  onCalendarSelect,
  onApplyDatePreset,
  onClearAll,
}: AdvancedFiltersProps) {
  const { t } = useI18n()

  const datePresets = [
    { label: t('date_preset_today'), from: new Date(), to: new Date() },
    { label: t('date_preset_yesterday'), from: subDays(new Date(), 1), to: subDays(new Date(), 1) },
    { label: t('date_preset_last_7'), from: subDays(new Date(), 6), to: new Date() },
    { label: t('date_preset_last_30'), from: subDays(new Date(), 29), to: new Date() },
    { label: t('date_preset_this_week'), from: startOfWeek(new Date(), { locale: es }), to: endOfWeek(new Date(), { locale: es }) },
    { label: t('date_preset_last_week'), from: startOfWeek(subWeeks(new Date(), 1), { locale: es }), to: endOfWeek(subWeeks(new Date(), 1), { locale: es }) },
    { label: t('date_preset_this_month'), from: startOfMonth(new Date()), to: endOfMonth(new Date()) },
    { label: t('date_preset_last_month'), from: startOfMonth(subMonths(new Date(), 1)), to: endOfMonth(subMonths(new Date(), 1)) },
  ]

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-9 gap-1">
          <ListFilter className="h-3.5 w-3.5" />
          <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">{t('filter')}</span>
          {hasActiveFilters && <span className="ml-0.5 h-1.5 w-1.5 rounded-full bg-primary" />}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-auto p-0">
        <div className="p-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Filtrar por
          </p>
        </div>

        <Separator />

        {/* Ubicación */}
        <div className="p-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            {t('label_ubicacion')}
          </p>
          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <Checkbox
                checked={!filters.ubicacion}
                onCheckedChange={(checked) => {
                  if (checked) onFilterChange({ ubicacion: undefined })
                }}
              />
              {t('all_feminine')}
            </label>
            {filterOptions.ubicaciones.map((ub) => (
              <label key={ub} className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <Checkbox
                  checked={filters.ubicacion === ub}
                  onCheckedChange={(checked) =>
                    onFilterChange({ ubicacion: checked ? ub : undefined })
                  }
                />
                {ub}
              </label>
            ))}
          </div>
        </div>

        <Separator />

        {/* Ciudad */}
        <div className="p-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            {t('label_ciudad')}
          </p>
          <div className="space-y-1.5 max-h-36 overflow-y-auto">
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <Checkbox
                checked={!filters.ciudad}
                onCheckedChange={(checked) => {
                  if (checked) onFilterChange({ ciudad: undefined })
                }}
              />
              {t('all_feminine')}
            </label>
            {filterOptions.ciudades.map((c) => (
              <label key={c} className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <Checkbox
                  checked={filters.ciudad === c}
                  onCheckedChange={(checked) =>
                    onFilterChange({ ciudad: checked ? c : undefined })
                  }
                />
                {c}
              </label>
            ))}
          </div>
        </div>

        <Separator />

        {/* Fecha de alta */}
        <div className="p-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Fecha de alta
          </p>
          <div className="flex flex-wrap gap-1 mb-2">
            {datePresets.map(({ label, from, to }) => (
              <Button
                key={label}
                variant="outline"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => onApplyDatePreset(from, to)}
              >
                {label}
              </Button>
            ))}
          </div>
          <Calendar
            mode="range"
            selected={localDateRange}
            onSelect={onCalendarSelect}
            locale={es}
            numberOfMonths={2}
            className="rounded-md border p-0"
          />
          {localDateRange?.from && (
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-muted-foreground">
                {localDateRange.to
                  ? `${format(localDateRange.from, 'dd/MM/yy')} – ${format(localDateRange.to, 'dd/MM/yy')}`
                  : format(localDateRange.from, 'dd/MM/yy')}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => onCalendarSelect(undefined)}
              >
                <X className="mr-1 h-3 w-3" />
                {t('clear_date')}
              </Button>
            </div>
          )}
        </div>

        {hasActiveFilters && (
          <>
            <Separator />
            <div className="p-3">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-muted-foreground"
                onClick={onClearAll}
              >
                <X className="mr-1 h-3 w-3" />
                Limpiar filtros
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}

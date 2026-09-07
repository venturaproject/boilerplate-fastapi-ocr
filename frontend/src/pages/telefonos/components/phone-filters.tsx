import { ListFilter, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useI18n } from '@/i18n/context'
import { TelefonoFilters, PhoneFilterOptions } from '../types'

interface PhoneFiltersProps {
  filters: TelefonoFilters
  filterOptions: PhoneFilterOptions
  hasActiveFilters: boolean
  onFilterChange: (partial: Partial<TelefonoFilters>) => void
  onClearAll: () => void
}

export function PhoneFilters({
  filters,
  filterOptions,
  hasActiveFilters,
  onFilterChange,
  onClearAll,
}: PhoneFiltersProps) {
  const { t } = useI18n()

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
            {t('filter_by')}
          </p>
        </div>

        <Separator />

        {/* Plan */}
        <div className="p-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            {t('col_plan')}
          </p>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <Checkbox
                checked={!filters.plan}
                onCheckedChange={(checked) => {
                  if (checked) onFilterChange({ plan: undefined })
                }}
              />
              {t('all_feminine')}
            </label>
            {filterOptions.planes.map((p) => (
              <label key={p} className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <Checkbox
                  checked={filters.plan === p}
                  onCheckedChange={(checked) =>
                    onFilterChange({ plan: checked ? p : undefined })
                  }
                />
                {p}
              </label>
            ))}
          </div>
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
                {t('clear_filters')}
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}

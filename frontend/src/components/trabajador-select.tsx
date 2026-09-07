import { useState, useMemo } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { TrabajadorOption } from '@/pages/dispositivos/types'

interface TrabajadorSelectProps {
  value?: number | null
  onChange: (value: number | null) => void
  options: TrabajadorOption[]
  placeholder?: string
  disabled?: boolean
}

export function TrabajadorSelect({
  value,
  onChange,
  options,
  placeholder = 'Buscar...',
  disabled,
}: TrabajadorSelectProps) {
  const [open, setOpen] = useState(false)

  const selectedLabel = useMemo(() => {
    if (value == null) return ''
    const found = options.find((o) => o.synergy_res_id === value)
    return found ? `${found.synergy_res_id} — ${found.nombre_completo}` : ''
  }, [value, options])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn('truncate', !selectedLabel && 'text-muted-foreground')}>
            {selectedLabel || placeholder}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <Command>
          <CommandInput placeholder={placeholder} />
          <CommandList>
            <CommandEmpty>No se encontraron empleados.</CommandEmpty>
            <CommandGroup>
              {options.map((opt) => (
                <CommandItem
                  key={opt.synergy_res_id}
                  value={`${opt.synergy_res_id} ${opt.nombre_completo}`.toLowerCase()}
                  onSelect={() => {
                    onChange(opt.synergy_res_id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      'mr-2 h-4 w-4',
                      value === opt.synergy_res_id ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <span className="font-mono text-xs text-muted-foreground mr-2">
                    {opt.synergy_res_id}
                  </span>
                  <span className="truncate">{opt.nombre_completo}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

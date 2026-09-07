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

export interface PhoneOption {
  id: number
  telefono: string
}

interface PhoneLineSelectProps {
  value?: string | null
  onChange: (value: string | null) => void
  options: PhoneOption[]
  placeholder?: string
  disabled?: boolean
}

export function PhoneLineSelect({
  value,
  onChange,
  options,
  placeholder = 'Buscar línea...',
  disabled,
}: PhoneLineSelectProps) {
  const [open, setOpen] = useState(false)

  const selectedLabel = useMemo(() => {
    if (!value) return ''
    const found = options.find((o) => o.telefono === value)
    return found?.telefono ?? value
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
            <CommandEmpty>No se encontraron líneas.</CommandEmpty>
            <CommandGroup>
              {options.map((opt) => (
                <CommandItem
                  key={opt.id}
                  value={opt.telefono}
                  onSelect={() => {
                    onChange(opt.telefono)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      'mr-2 h-4 w-4',
                      value === opt.telefono ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <span className="font-mono">{opt.telefono}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

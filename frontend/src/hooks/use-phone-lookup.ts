import { useQuery } from '@tanstack/react-query'
import { LOOKUP_CACHE_STALE_MS } from '@/lib/constants'

async function fetchPhoneLookup(numbers: string[]): Promise<Record<string, number>> {
  const params = new URLSearchParams()
  numbers.forEach((n) => params.append('numbers[]', n))

  const res = await fetch(`${route('api.phone-lookup')}?${params.toString()}`)
  if (!res.ok) throw new Error(`Phone lookup failed: ${res.status}`)
  return res.json() as Promise<Record<string, number>>
}

/**
 * Lookup phone IDs by phone numbers usando React Query.
 * La caché se invalida automáticamente según LOOKUP_CACHE_STALE_MS.
 *
 * Usage:
 *   const phoneMap = usePhoneLookup(['605789935', '607280712'])
 *   const id = phoneMap['605789935'] // number | undefined
 */
export function usePhoneLookup(numbers: string[]): Record<string, number> {
  // Ordenar para clave de caché estable independientemente del orden de entrada
  const sortedNumbers = [...numbers].sort()
  const queryKey = ['phone-lookup', sortedNumbers] as const

  const { data } = useQuery({
    queryKey,
    queryFn: () => fetchPhoneLookup(sortedNumbers),
    staleTime: LOOKUP_CACHE_STALE_MS,
    // No reintentar en errores — el componente simplemente no mostrará el link
    retry: false,
    // No refrescar al recuperar foco de ventana
    refetchOnWindowFocus: false,
    // Solo hacer fetch si hay números que buscar
    enabled: sortedNumbers.length > 0,
  })

  return data ?? {}
}

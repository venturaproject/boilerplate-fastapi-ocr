import { CardFooter } from '@/components/ui/card'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

interface PaginationFooterProps {
  currentPage: number
  lastPage: number
  perPage: number
  total: number
  noun?: string
  onPageChange: (page: number) => void
}

/**
 * The list-page footer used across the admin — a "showing X–Y of Z" count on
 * the left and a numbered pager on the right (same shape as the Roles /
 * Permissions tables).
 */
export function PaginationFooter({
  currentPage,
  lastPage,
  perPage,
  total,
  noun = 'resultados',
  onPageChange,
}: PaginationFooterProps) {
  const start = total === 0 ? 0 : (currentPage - 1) * perPage + 1
  const end = Math.min(currentPage * perPage, total)

  const pageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = []
    const delta = 2
    const rangeStart = Math.max(2, currentPage - delta)
    const rangeEnd = Math.min(lastPage - 1, currentPage + delta)

    if (lastPage > 1) pages.push(1)
    if (rangeStart > 2) pages.push('...')
    for (let i = rangeStart; i <= rangeEnd; i++) {
      if (i !== 1 && i !== lastPage) pages.push(i)
    }
    if (rangeEnd < lastPage - 1) pages.push('...')
    if (lastPage > 1) pages.push(lastPage)

    return pages
  }

  return (
    <CardFooter className="flex flex-col sm:flex-row items-center justify-between gap-4">
      <div className="text-xs text-muted-foreground">
        Mostrando {start}-{end} de {total} {noun}
      </div>

      {lastPage > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  if (currentPage > 1) onPageChange(currentPage - 1)
                }}
                className={currentPage === 1 ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>

            {pageNumbers().map((page, index) => (
              <PaginationItem key={index}>
                {page === '...' ? (
                  <span className="flex h-9 w-9 items-center justify-center text-sm">...</span>
                ) : (
                  <PaginationLink
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      onPageChange(page as number)
                    }}
                    isActive={page === currentPage}
                  >
                    {page}
                  </PaginationLink>
                )}
              </PaginationItem>
            ))}

            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  if (currentPage < lastPage) onPageChange(currentPage + 1)
                }}
                className={currentPage === lastPage ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </CardFooter>
  )
}

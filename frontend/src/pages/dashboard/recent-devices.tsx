import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { Smartphone, User } from 'lucide-react'
import { useI18n } from '@/i18n/context'

interface RecentDevice {
  id: number
  marca: string | null
  modelo: string | null
  numero: string | null
  grupo: string | null
  employee_nombre: string | null
  updated_at: string
}

interface RecentDevicesProps {
  devices: RecentDevice[]
}

export function RecentDevices({ devices }: RecentDevicesProps) {
  const { t } = useI18n()

  if (devices.length === 0) {
    return (
      <div className='text-center py-8 text-muted-foreground'>
        {t('no_recent_devices')}
      </div>
    )
  }

  return (
    <div className='space-y-6'>
      {devices.map((device) => (
        <div key={device.id} className='flex items-start gap-3'>
          <div className='mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-muted'>
            <Smartphone className='h-4 w-4 text-muted-foreground' />
          </div>
          <div className='flex flex-1 flex-col gap-0.5'>
            <p className='text-sm font-medium leading-none'>
              {device.marca} {device.modelo}
            </p>
            <p className='text-xs text-muted-foreground'>
              {device.grupo && (
                <span className='mr-1'>{device.grupo}</span>
              )}
              {device.numero && (
                <span className='font-mono'>{device.numero}</span>
              )}
              {!device.grupo && !device.numero && (
                <span>—</span>
              )}
            </p>
            <div className='flex items-center gap-1 text-xs text-muted-foreground mt-0.5'>
              {device.employee_nombre ? (
                <>
                  <User className='h-3 w-3' />
                  <span>{device.employee_nombre}</span>
                </>
              ) : (
                <span>{t('unassigned')}</span>
              )}
            </div>
          </div>
          <div className='text-xs text-muted-foreground shrink-0'>
            {formatDistanceToNow(new Date(device.updated_at), { addSuffix: true, locale: es })}
          </div>
        </div>
      ))}
    </div>
  )
}

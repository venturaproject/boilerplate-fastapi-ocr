import { useState } from 'react'
import { ArrowLeft, Edit, Package } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DeliverDeviceModal } from '@/components/deliver-device-modal'
import { DeliveryReceiptsTable } from '@/components/delivery-receipts-table'
import { DevicePhonesTable } from '@/components/device-phones-table'
import { DeviceEmployeesTable } from '@/components/device-employees-table'
import { useI18n } from '@/i18n/context'
import { pathFor } from '@/lib/app-routes'
import { Dispositivo, DeliveryReceipt, AssociatedPhone, AssociatedEmployee } from './types'

interface DispositivoShowProps {
  device: Dispositivo
  deliveryReceipts: DeliveryReceipt[]
  associatedPhones: AssociatedPhone[]
  associatedEmployees: AssociatedEmployee[]
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex items-center justify-between py-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value || '-'}</dd>
    </div>
  )
}

export default function DispositivoShow({
  device,
  deliveryReceipts = [],
  associatedPhones = [],
  associatedEmployees = [],
}: DispositivoShowProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [openDeliver, setOpenDeliver] = useState(false)

  const hasAssociations = associatedPhones.length > 0 || associatedEmployees.length > 0 || deliveryReceipts.length > 0

  return (
    <AuthenticatedLayout title={t('dispositivos_title')}>
      <Main>
        <div className="flex-1 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex-1 space-y-1">
              <h1 className="text-2xl font-bold tracking-tight">
                {device.marca} {device.modelo}
              </h1>
              <p className="text-muted-foreground">
                {t('dispositivo_detail_title', { id: device.id })}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setOpenDeliver(true)}
              >
                <Package className="mr-2 h-4 w-4" />
                Entregar
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate(pathFor('admin.dispositivos.index'))}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('back')}
              </Button>
              <Button
                variant="default"
                onClick={() => navigate(pathFor('admin.dispositivos.edit', device.id))}
              >
                <Edit className="mr-2 h-4 w-4" />
                {t('edit_device')}
              </Button>
            </div>
          </div>

          {/* Device Info Cards */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t('dispositivo_info_general')}</CardTitle>
                <CardDescription>{t('dispositivo_info_general_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="space-y-1">
                  <InfoRow label={t('col_marca')} value={device.marca} />
                  <Separator />
                  <InfoRow label={t('col_modelo')} value={device.modelo} />
                  <Separator />
                  <InfoRow label={t('col_imei')} value={device.imei} />
                  <Separator />
                  <InfoRow label={t('col_numero')} value={device.numero} />
                  <Separator />
                  <div className="flex items-center justify-between py-3">
                    <dt className="text-sm text-muted-foreground">{t('col_grupo')}</dt>
                    <dd>
                      {device.grupo ? (
                        <Badge variant="secondary">{device.grupo}</Badge>
                      ) : '-'}
                    </dd>
                  </div>
                  <Separator />
                  <InfoRow label={t('col_otros')} value={device.otros} />
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>{t('dispositivo_asignacion')}</CardTitle>
                <CardDescription>{t('dispositivo_asignacion_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="space-y-1">
                  <div className="flex items-center justify-between py-3">
                    <dt className="text-sm text-muted-foreground">{t('col_trabajador')}</dt>
                    <dd>
                      {device.employee ? (
                        <Badge variant="secondary">{device.employee.nombre_completo}</Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">—</span>
                      )}
                    </dd>
                  </div>
                  <Separator />
                  <InfoRow
                    label={t('col_employee_synergy_id')}
                    value={device.employee_synergy_res_id?.toString() ?? null}
                  />
                </dl>
              </CardContent>
            </Card>
          </div>

          {/* Association Tabs */}
          {hasAssociations && (
            <Tabs defaultValue="phones">
              <TabsList>
                <TabsTrigger value="phones">
                  Teléfonos
                  {associatedPhones.length > 0 && (
                    <Badge variant="secondary" className="ml-1.5 h-5 min-w-5 px-1.5">
                      {associatedPhones.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="employees">
                  Trabajadores
                  {associatedEmployees.length > 0 && (
                    <Badge variant="secondary" className="ml-1.5 h-5 min-w-5 px-1.5">
                      {associatedEmployees.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="receipts">
                  Acuses
                  {deliveryReceipts.length > 0 && (
                    <Badge variant="secondary" className="ml-1.5 h-5 min-w-5 px-1.5">
                      {deliveryReceipts.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="phones">
                <DevicePhonesTable phones={associatedPhones} />
              </TabsContent>

              <TabsContent value="employees">
                <DeviceEmployeesTable employees={associatedEmployees} />
              </TabsContent>

              <TabsContent value="receipts">
                <DeliveryReceiptsTable receipts={deliveryReceipts} />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </Main>

      <DeliverDeviceModal
        device={device}
        open={openDeliver}
        onOpenChange={setOpenDeliver}
      />
    </AuthenticatedLayout>
  )
}

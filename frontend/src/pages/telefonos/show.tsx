import { AuthenticatedLayout } from "@/layouts"
import { Main } from "@/components/layout"
import { ArrowLeft, PhoneOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ConfirmDialog } from "@/components/confirm-dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PhoneHistoryTable } from "@/components/phone-history-table"
import { PhoneActionTable } from "@/components/phone-action-table"
import { useI18n } from "@/i18n/context"
import { pathFor } from "@/lib/app-routes"
import { telefonosApi } from "@/services/telefonos-api"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

interface PhoneStatus {
  id: number
  nombre: string
}

interface Trabajador {
  id: number
  nombre_completo: string
  telefono_synergy: string | null
}

interface Telefono {
  id: number
  telefono: string
  plan: string
  nplan: string
  tipo: string
  pin: string | null
  puk: string | null
  estado_telefonos_id: number
  tipologias_id: number | null
  notas: string | null
  status: PhoneStatus | null
  trabajador: Trabajador | null
  created_at: string
  updated_at: string
}

interface PhoneHistory {
  id: number
  llamadas: string
  datos: string
  pagina_gored: number | null
  created_at: string
}

interface PhoneAction {
  id: number
  nombre: string
  user: { name: string } | null
  created_at: string
}

interface ShowPhoneProps {
  phone: Telefono
  history: PhoneHistory[]
  actions: PhoneAction[]
}

export default function ShowPhone({ phone, history = [], actions = [] }: ShowPhoneProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [confirmDesactivar, setConfirmDesactivar] = useState(false)

  const handleDesactivar = () => {
    setConfirmDesactivar(false)
    telefonosApi.desactivar(phone.id)
      .then(() => {
        toast.warning(`${t('line_deactivated')}: ${phone.telefono}`)
        navigate(pathFor('admin.telefonos.index'))
      })
      .catch(() => toast.error(t('please_try_again')))
  }

  const InfoRow = ({ label, value }: { label: string; value: string }) => (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )

  return (
    <AuthenticatedLayout title={`Teléfono ${phone.telefono}`}>
      <Main>
        <div className="flex-1 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex-1 space-y-1">
              <h1 className="text-2xl font-bold tracking-tight">Teléfono {phone.telefono}</h1>
              <p className="text-muted-foreground">Detalle del teléfono</p>
            </div>
            <div className="flex items-center gap-2">
              {phone.estado_telefonos_id !== 3 && (
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setConfirmDesactivar(true)}
                >
                  <PhoneOff className="mr-2 h-4 w-4" />
                  {t('action_desactivar')}
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => navigate(pathFor('admin.telefonos.index'))}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver
              </Button>
              <Button
                onClick={() => navigate(pathFor('admin.telefonos.edit', phone.id))}
              >
                Editar
              </Button>
            </div>
          </div>

          {/* Información Principal */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Información Principal */}
            <div className="rounded-lg border p-4 space-y-2">
              <h3 className="font-medium">Información Principal</h3>
              <Separator />
              <InfoRow label="Número" value={phone.telefono} />
              <InfoRow label="Tipo" value={phone.tipo || '-'} />
              <InfoRow label="Plan" value={phone.plan || '-'} />
              <InfoRow label="NPlan" value={phone.nplan || '-'} />
            </div>

            {/* Códigos de Seguridad */}
            <div className="rounded-lg border p-4 space-y-2">
              <h3 className="font-medium">Códigos de Seguridad</h3>
              <Separator />
              <InfoRow label="PIN" value={phone.pin || '-'} />
              <InfoRow label="PUK" value={phone.puk || '-'} />
            </div>

            {/* Estado */}
            <div className="rounded-lg border p-4 space-y-2">
              <h3 className="font-medium">Estado</h3>
              <Separator />
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-muted-foreground">Estado</span>
                <Badge variant={phone.estado_telefonos_id === 1 ? 'default' : 'secondary'}>
                  {phone.status?.nombre || 'Desconocido'}
                </Badge>
              </div>
              <InfoRow label="Creado" value={new Date(phone.created_at).toLocaleDateString('es-ES')} />
              <InfoRow label="Actualizado" value={new Date(phone.updated_at).toLocaleDateString('es-ES')} />
            </div>

            {/* Asignación */}
            <div className="rounded-lg border p-4 space-y-2">
              <h3 className="font-medium">Asignación</h3>
              <Separator />
              <InfoRow label="Trabajador" value={phone.trabajador?.nombre_completo || 'No asignado'} />
              {phone.trabajador && (
                <div className="rounded-md bg-muted/50 p-2 text-sm">
                  <span className="text-muted-foreground">Synergy:</span>
                  <span className="ml-2 font-mono">{phone.trabajador.telefono_synergy || 'No disponible'}</span>
                </div>
              )}
            </div>

            {/* Notas */}
            <div className="rounded-lg border p-4 space-y-2 md:col-span-2 lg:col-span-2">
              <h3 className="font-medium">Notas</h3>
              <Separator />
              <p className="text-sm text-muted-foreground">{phone.notas || 'Sin notas'}</p>
            </div>
          </div>

          {/* Tabs: Histórico y Actuaciones */}
          <Tabs defaultValue="history">
            <TabsList>
              <TabsTrigger value="history">Histórico</TabsTrigger>
              <TabsTrigger value="actions">Actuaciones</TabsTrigger>
            </TabsList>

            <TabsContent value="history">
              <PhoneHistoryTable history={history} />
            </TabsContent>

            <TabsContent value="actions">
              <PhoneActionTable phoneId={phone.id} actions={actions} />
            </TabsContent>
          </Tabs>
        </div>
      </Main>

      <ConfirmDialog
        open={confirmDesactivar}
        onOpenChange={setConfirmDesactivar}
        title={t('confirm_desactivar_title')}
        desc={t('confirm_desactivar_desc', { telefono: phone.telefono })}
        destructive
        handleConfirm={handleDesactivar}
        confirmText={t('action_desactivar')}
        cancelBtnText={t('cancel')}
      />
    </AuthenticatedLayout>
  )
}

import { AuthenticatedLayout } from "@/layouts"
import { Main } from "@/components/layout"
import { ArrowLeft, Save, PhoneOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/confirm-dialog"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PhoneHistoryTable } from "@/components/phone-history-table"
import { PhoneActionTable } from "@/components/phone-action-table"
import { useI18n } from "@/i18n/context"
import { pathFor } from "@/lib/app-routes"
import { telefonosApi } from "@/services/telefonos-api"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { useFlashToast } from "@/hooks/use-flash-toast"

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

interface EditPhoneProps {
  phone: Telefono
  statuses: PhoneStatus[]
  tipologiaOptions: Record<number, string>
  history: PhoneHistory[]
  actions: PhoneAction[]
}

interface PhoneForm {
  telefono: string
  tipo: string
  plan: string
  nplan: string
  pin: string
  puk: string
  estado_telefonos_id: string
  notas: string
  tipologias_id: string
}

export default function EditPhone({ phone, statuses: initialStatuses = [], tipologiaOptions, history = [], actions = [] }: EditPhoneProps) {
  const options = tipologiaOptions != null ? tipologiaOptions : {}
  const { t } = useI18n()
  const navigate = useNavigate()
  useFlashToast()
  const [statuses] = useState<PhoneStatus[]>(initialStatuses)
  const [confirmDesactivar, setConfirmDesactivar] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [errors, setErrors] = useState<Partial<Record<keyof PhoneForm, string>>>({})
  const [data, setData] = useState<PhoneForm>({
    telefono: phone.telefono || '',
    tipo: phone.tipo || '',
    plan: phone.plan || '',
    nplan: phone.nplan || '',
    pin: phone.pin || '',
    puk: phone.puk || '',
    estado_telefonos_id: String(phone.estado_telefonos_id),
    notas: phone.notas || '',
    tipologias_id: String(phone.tipologias_id || ''),
  })

  const updateField = <K extends keyof PhoneForm>(key: K, value: PhoneForm[K]) => {
    setData((prev) => ({ ...prev, [key]: value }))
  }

  const handleDesactivar = () => {
    setConfirmDesactivar(false)
    telefonosApi.desactivar(phone.id)
      .then(() => {
        toast.warning(`${t('line_deactivated')}: ${phone.telefono}`)
        navigate(pathFor('admin.telefonos.index'))
      })
      .catch(() => toast.error(t('please_try_again')))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setProcessing(true)
    setErrors({})
    telefonosApi.update(phone.id, data)
      .then(() => {
        toast.success(t('phone_updated_desc'))
      })
      .catch((error: any) => {
        const serverErrors = error?.response?.data?.errors ?? {}
        setErrors(serverErrors)
        toast.error(Object.values(serverErrors)[0] as string || t('please_check_form'))
      })
      .finally(() => {
        setProcessing(false)
      })
  }

  return (
    <AuthenticatedLayout title={`Editar teléfono ${phone.telefono}`}>
      <Main>
        <div className="flex-1 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex-1 space-y-1">
              <h1 className="text-2xl font-bold tracking-tight">Editar Teléfono</h1>
              <p className="text-muted-foreground">{phone.telefono}</p>
            </div>
            <div className="flex items-center gap-2">
              {phone.estado_telefonos_id !== 3 && (
                <Button
                  type="button"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setConfirmDesactivar(true)}
                >
                  <PhoneOff className="mr-2 h-4 w-4" />
                  {t('action_desactivar')}
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate(pathFor('admin.telefonos.show', phone.id))}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Ver Detalle
              </Button>
              <Button onClick={() => (document.querySelector('form') as HTMLFormElement)?.requestSubmit()}>
                <Save className="mr-2 h-4 w-4" />
                {processing ? 'Guardando...' : 'Guardar cambios'}
              </Button>
            </div>
          </div>

          {/* Formulario de Edición */}
          <form onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
                  {/* Información Principal */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Información Principal</CardTitle>
                      <CardDescription>
                        Actualiza la información básica del teléfono
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {phone.trabajador && (
                        <div className="space-y-2 rounded-md border bg-muted/50 p-3">
                          <Label>Trabajador asignado</Label>
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{phone.trabajador.nombre_completo}</span>
                            <span className="text-xs text-muted-foreground">ID: {phone.trabajador.id}</span>
                          </div>
                          {phone.trabajador.telefono_synergy && (
                            <div className="text-sm text-muted-foreground">
                              Teléfono Synergy: <span className="font-mono">{phone.trabajador.telefono_synergy}</span>
                            </div>
                          )}
                          <p className="text-xs text-muted-foreground">
                            La asignación se gestiona automáticamente mediante la sincronización con Synergy.
                          </p>
                        </div>
                      )}
                      <div className="space-y-2">
                        <Label htmlFor="telefono">Número de teléfono</Label>
                        <Input
                          id="telefono"
                          value={data.telefono}
                          readOnly
                          disabled
                          className="cursor-not-allowed opacity-60"
                        />
                        <p className="text-xs text-muted-foreground">Asignado automáticamente por el scraping.</p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="tipo">Tipo</Label>
                        <Input
                          id="tipo"
                          value={data.tipo}
                          onChange={(e) => updateField('tipo', e.target.value)}
                          placeholder="Ej: Móvil"
                        />
                        {errors.tipo && (
                          <p className="text-sm text-red-500">{errors.tipo as string}</p>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="plan">Plan</Label>
                          <Input
                            id="plan"
                            value={data.plan}
                            onChange={(e) => updateField('plan', e.target.value)}
                            placeholder="Ej: Empresa"
                          />
                          {errors.plan && (
                            <p className="text-sm text-red-500">{errors.plan as string}</p>
                          )}
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="nplan">NPlan</Label>
                          <Input
                            id="nplan"
                            value={data.nplan}
                            onChange={(e) => updateField('nplan', e.target.value)}
                            placeholder="Ej: Nuevo Plan"
                          />
                          {errors.nplan && (
                            <p className="text-sm text-red-500">{errors.nplan as string}</p>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Códigos de Seguridad */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Códigos de Seguridad</CardTitle>
                      <CardDescription>
                        PIN y PUK del teléfono
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="pin">PIN</Label>
                        <Input
                          id="pin"
                          value={data.pin}
                          onChange={(e) => updateField('pin', e.target.value)}
                          placeholder="Ej: 1234"
                          maxLength={20}
                        />
                        {errors.pin && (
                          <p className="text-sm text-red-500">{errors.pin as string}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="puk">PUK</Label>
                        <Input
                          id="puk"
                          value={data.puk}
                          onChange={(e) => updateField('puk', e.target.value)}
                          placeholder="Ej: 12345678"
                          maxLength={20}
                        />
                        {errors.puk && (
                          <p className="text-sm text-red-500">{errors.puk as string}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Estado */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Estado</CardTitle>
                      <CardDescription>
                        Estado actual del teléfono
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="estado_telefonos_id">Estado *</Label>
                        <Select
                          value={data.estado_telefonos_id}
                          onValueChange={(value) => updateField('estado_telefonos_id', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Selecciona un estado" />
                          </SelectTrigger>
                          <SelectContent>
                            {statuses.map((status) => (
                              <SelectItem key={status.id} value={String(status.id)}>
                                {status.nombre}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.estado_telefonos_id && (
                          <p className="text-sm text-red-500">{errors.estado_telefonos_id as string}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="tipologias_id">Tipología</Label>
                        <Select
                          value={data.tipologias_id || 'none'}
                          onValueChange={(value) => updateField('tipologias_id', value === 'none' ? '' : value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Selecciona una tipología" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">— Sin tipología —</SelectItem>
                            {Object.entries(options).map(([id, label]) => (
                              <SelectItem key={id} value={id}>
                                {String(label)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.tipologias_id && (
                          <p className="text-sm text-red-500">{errors.tipologias_id as string}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Notas */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Notas</CardTitle>
                      <CardDescription>
                        Notas adicionales sobre el teléfono
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="notas">Notas</Label>
                        <Textarea
                          id="notas"
                          value={data.notas}
                          onChange={(e) => updateField('notas', e.target.value)}
                          placeholder="Añade notas sobre este teléfono..."
                          rows={4}
                        />
                        {errors.notas && (
                          <p className="text-sm text-red-500">{errors.notas as string}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </form>

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

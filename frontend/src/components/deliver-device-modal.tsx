import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { SignatureCanvas } from '@/components/signature-canvas'
import { useI18n } from '@/i18n/context'
import { dispositivosApi } from '@/services/dispositivos-api'
import { toast } from 'sonner'

interface Device {
  id: number
  marca: string | null
  modelo: string | null
  imei: string | null
  numero: string | null
  grupo: string | null
  employee_synergy_res_id: number | null
  employee?: { nombre_completo: string; email: string | null } | null
}

interface DeliverDeviceModalProps {
  device: Device
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DeliverDeviceModal({ device, open, onOpenChange }: DeliverDeviceModalProps) {
  const { t } = useI18n()
  const [signature, setSignature] = useState<string | null>(null)
  const [emailTo, setEmailTo] = useState(device.employee?.email ?? '')
  const [loading, setLoading] = useState(false)

  const handleSubmit = () => {
    if (!signature) {
      toast.error('Por favor, captura la firma del empleado.')
      return
    }

    setLoading(true)
    dispositivosApi.deliver(device.id, {
        signature,
        employee_synergy_res_id: device.employee_synergy_res_id,
      })
      .then(() => {
        toast.success('Entrega registrada')
        onOpenChange(false)
      })
      .catch(() => {
        toast.error(t('please_try_again'))
      })
      .finally(() => {
        setLoading(false)
      })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Entregar Dispositivo</DialogTitle>
          <DialogDescription>
            Registra la entrega del dispositivo con la firma del empleado.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Device Info */}
          <div className="rounded-lg bg-muted/50 p-4 space-y-2">
            <h4 className="font-medium">Información del Dispositivo</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Marca:</span>{' '}
                <span className="font-medium">{device.marca ?? '-'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Modelo:</span>{' '}
                <span className="font-medium">{device.modelo ?? '-'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">IMEI:</span>{' '}
                <span className="font-mono">{device.imei ?? '-'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Número:</span>{' '}
                <span className="font-mono">{device.numero ?? '-'}</span>
              </div>
            </div>
          </div>

          {/* Employee Info */}
          {device.employee && (
            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
              <h4 className="font-medium">Empleado</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Nombre:</span>{' '}
                  <span className="font-medium">{device.employee.nombre_completo}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Email:</span>{' '}
                  <span>{device.employee.email ?? '-'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Email Field */}
          <div className="space-y-2">
            <Label htmlFor="email">Email para acuse (opcional)</Label>
            <Input
              id="email"
              type="email"
              value={emailTo}
              onChange={(e) => setEmailTo(e.target.value)}
              placeholder="empleado@ejemplo.com"
            />
          </div>

          {/* Signature */}
          <div className="space-y-2">
            <Label>Firma del Empleado *</Label>
            <SignatureCanvas
              onSignatureChange={setSignature}
              width={560}
              height={180}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !signature}>
            {loading ? 'Registrando...' : 'Registrar Entrega'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

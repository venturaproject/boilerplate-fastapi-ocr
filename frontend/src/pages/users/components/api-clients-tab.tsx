import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Copy, Trash2, Plus, ShieldOff, Check, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { apiClientsApi, ApiClientRecord, AVAILABLE_SCOPES } from '@/services/api-clients-api'

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={handleCopy} title="Copiar">
      {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
    </Button>
  )
}

// ── Secret reveal modal ────────────────────────────────────────────────────────

interface SecretModalProps {
  open: boolean
  onClose: () => void
  clientId: string
  secret: string
}

function SecretModal({ open, onClose, clientId, secret }: SecretModalProps) {
  const [revealed, setRevealed] = useState(false)
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Cliente API creado</DialogTitle>
          <DialogDescription>
            Guarda el secreto ahora — no podrás verlo de nuevo.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Client ID</Label>
            <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 font-mono text-sm">
              <span className="flex-1">{clientId}</span>
              <CopyButton text={clientId} />
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Client Secret</Label>
            <div className="flex items-center gap-2 rounded-md border border-yellow-400 bg-yellow-50 px-3 py-2 font-mono text-sm dark:bg-yellow-950/30">
              <span className="flex-1 break-all">
                {revealed ? secret : '•'.repeat(Math.min(secret.length, 40))}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={() => setRevealed((v) => !v)}
              >
                {revealed ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              </Button>
              <CopyButton text={secret} />
            </div>
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              Este secreto no volverá a mostrarse. Cópialo ahora.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={onClose}>Entendido</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Create dialog ─────────────────────────────────────────────────────────────

interface CreateDialogProps {
  open: boolean
  onClose: () => void
  onCreate: (name: string, scopes: string[]) => Promise<void>
  loading: boolean
}

function CreateDialog({ open, onClose, onCreate, loading }: CreateDialogProps) {
  const [name, setName] = useState('')
  const [scopes, setScopes] = useState<string[]>([])

  const toggleScope = (scope: string) => {
    if (scope === '*') {
      setScopes((prev) => (prev.includes('*') ? [] : ['*']))
      return
    }
    setScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev.filter((s) => s !== '*'), scope]
    )
  }

  const handleClose = () => {
    setName('')
    setScopes([])
    onClose()
  }

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error('El nombre es obligatorio'); return }
    if (scopes.length === 0) { toast.error('Selecciona al menos un scope'); return }
    await onCreate(name.trim(), scopes)
    setName('')
    setScopes([])
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nuevo cliente API</DialogTitle>
          <DialogDescription>
            Crea un cliente para acceder a la API externa con credenciales propias.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label htmlFor="client-name">Nombre del sistema</Label>
            <Input
              id="client-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ERP, Sistema externo…"
              onKeyDown={(e) => e.key === 'Enter' && !loading && handleSubmit()}
            />
          </div>

          <div className="space-y-2">
            <Label>Scopes (permisos)</Label>
            <div className="space-y-2 rounded-md border p-3">
              {AVAILABLE_SCOPES.map((s) => (
                <div key={s.value} className="flex items-center gap-2">
                  <Checkbox
                    id={`scope-${s.value}`}
                    checked={scopes.includes(s.value) || (s.value !== '*' && scopes.includes('*'))}
                    onCheckedChange={() => toggleScope(s.value)}
                    disabled={s.value !== '*' && scopes.includes('*')}
                  />
                  <Label htmlFor={`scope-${s.value}`} className="cursor-pointer text-sm font-normal">
                    {s.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Creando…' : 'Crear cliente'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────

export function ApiClientsTab() {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [secretModal, setSecretModal] = useState<{ clientId: string; secret: string } | null>(null)
  const [confirmRevoke, setConfirmRevoke] = useState<ApiClientRecord | null>(null)

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['api-clients'],
    queryFn: () => apiClientsApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: ({ name, scopes }: { name: string; scopes: string[] }) =>
      apiClientsApi.create({ name, scopes }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['api-clients'] })
      setCreateOpen(false)
      setSecretModal({ clientId: res.client.client_id, secret: res.secret })
    },
    onError: () => toast.error('Error al crear el cliente API'),
  })

  const revokeMutation = useMutation({
    mutationFn: (id: string) => apiClientsApi.revoke(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-clients'] })
      toast.success('Cliente revocado')
      setConfirmRevoke(null)
    },
    onError: () => toast.error('Error al revocar el cliente'),
  })

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>Clientes de API externa</CardTitle>
            <CardDescription className="mt-1">
              Gestiona los clientes que acceden a la API externa mediante Bearer token
            </CardDescription>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Nuevo cliente
          </Button>
        </CardHeader>

        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Client ID</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Último uso</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                    Cargando…
                  </TableCell>
                </TableRow>
              ) : clients.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                    No hay clientes API. Crea el primero.
                  </TableCell>
                </TableRow>
              ) : (
                clients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell className="font-medium">{client.name}</TableCell>

                    <TableCell>
                      <div className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
                        <span>{client.client_id}</span>
                        <CopyButton text={client.client_id} />
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {client.scopes.map((s) => (
                          <Badge key={s} variant="secondary" className="text-xs">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>

                    <TableCell>
                      {client.active ? (
                        <Badge variant="outline" className="border-green-500 text-green-600">
                          Activo
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="border-red-400 text-red-500">
                          Revocado
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="text-sm text-muted-foreground">
                      {client.last_used_at
                        ? new Date(client.last_used_at).toLocaleString()
                        : 'Nunca'}
                    </TableCell>

                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground hover:text-destructive"
                        disabled={!client.active}
                        onClick={() => setConfirmRevoke(client)}
                        title={client.active ? 'Revocar cliente' : 'Ya revocado'}
                      >
                        {client.active ? (
                          <Trash2 className="h-4 w-4" />
                        ) : (
                          <ShieldOff className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <CreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        loading={createMutation.isPending}
        onCreate={async (name, scopes) => { await createMutation.mutateAsync({ name, scopes }) }}
      />

      {secretModal && (
        <SecretModal
          open
          onClose={() => setSecretModal(null)}
          clientId={secretModal.clientId}
          secret={secretModal.secret}
        />
      )}

      <ConfirmDialog
        open={!!confirmRevoke}
        onOpenChange={(v) => !v && setConfirmRevoke(null)}
        title="Revocar cliente API"
        desc={`¿Revocar "${confirmRevoke?.name}"? Sus tokens dejarán de funcionar de inmediato.`}
        confirmText="Revocar"
        destructive
        handleConfirm={() => confirmRevoke && revokeMutation.mutate(confirmRevoke.id)}
      />
    </>
  )
}

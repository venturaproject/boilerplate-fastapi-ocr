import { useState } from 'react'
import { Plus, Trash2, FileText, Pencil } from 'lucide-react'
import { toast } from 'sonner'
import { useFlashToast } from '@/hooks/use-flash-toast'
import { axios } from '@/lib/axios'
import { endpoints } from '@/lib/endpoints'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/i18n/context'

interface PhoneAction {
  id: number
  nombre: string
  user: { name: string } | null
  created_at: string
}

interface PhoneActionTableProps {
  phoneId: number
  actions: PhoneAction[]
}

export function PhoneActionTable({ phoneId, actions = [] }: PhoneActionTableProps) {
  const { t } = useI18n()
  useFlashToast()
  const [items, setItems] = useState<PhoneAction[]>(actions)
  const [openCreateModal, setOpenCreateModal] = useState(false)
  const [openEditModal, setOpenEditModal] = useState(false)
  const [newAction, setNewAction] = useState('')
  const [editingAction, setEditingAction] = useState<PhoneAction | null>(null)
  const [editValue, setEditValue] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  const normalizeAction = (action: any): PhoneAction => ({
    id: action.id,
    nombre: action.nombre ?? action.descripcion ?? '',
    user: action.user ?? (action.usuario_nombre ? { name: action.usuario_nombre } : null),
    created_at: action.created_at ?? action.fecha ?? new Date().toISOString(),
  })

  const handleCreateAction = () => {
    if (!newAction.trim()) return
    setActionLoading(true)
    axios.post(endpoints.telefonos.actions.store(phoneId), {
      nombre: newAction,
    })
      .then((response) => {
        setItems((prev) => [normalizeAction(response.data), ...prev])
        setNewAction('')
        setOpenCreateModal(false)
      })
      .catch(() => {
        toast.error(t('please_try_again'))
      })
      .finally(() => {
        setActionLoading(false)
      })
  }

  const openEdit = (action: PhoneAction) => {
    setEditingAction(action)
    setEditValue(action.nombre)
    setOpenEditModal(true)
  }

  const handleUpdateAction = () => {
    if (!editingAction || !editValue.trim()) return
    setActionLoading(true)
    axios.put(endpoints.telefonos.actions.detail(editingAction.id), {
      nombre: editValue,
    })
      .then((response) => {
        setItems((prev) =>
          prev.map((item) => (item.id === editingAction.id ? normalizeAction({ ...item, ...response.data }) : item))
        )
        setEditValue('')
        setEditingAction(null)
        setOpenEditModal(false)
      })
      .catch(() => {
        toast.error(t('please_try_again'))
      })
      .finally(() => {
        setActionLoading(false)
      })
  }

  const handleDeleteAction = (actionId: number) => {
    axios.delete(endpoints.telefonos.actions.detail(actionId))
      .then(() => {
        setItems((prev) => prev.filter((item) => item.id !== actionId))
        toast.success(t('action_deleted'))
      })
      .catch(() => {
        toast.error(t('please_try_again'))
      })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5" />
            Actuaciones
          </CardTitle>
          <Button size="sm" onClick={() => setOpenCreateModal(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Añadir
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin actuaciones registradas</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Actuación</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead className="text-right">Fecha</TableHead>
                <TableHead className="w-[100px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((action) => (
                <TableRow key={action.id}>
                  <TableCell className="font-medium">{action.nombre}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {action.user?.name || '-'}
                  </TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {new Date(action.created_at).toLocaleDateString('es-ES', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => openEdit(action)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => handleDeleteAction(action.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create Modal */}
      <Dialog open={openCreateModal} onOpenChange={setOpenCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva actuación</DialogTitle>
            <DialogDescription>
              Registra una nueva actuación para este teléfono.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="new-action">Descripción</Label>
              <Textarea
                id="new-action"
                value={newAction}
                onChange={(e) => setNewAction(e.target.value)}
                placeholder="Describe la actuación realizada..."
                rows={3}
                onKeyDown={(e) => e.key === 'Enter' && e.ctrlKey && handleCreateAction()}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenCreateModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleCreateAction} disabled={actionLoading || !newAction.trim()}>
              {actionLoading ? 'Guardando...' : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={openEditModal} onOpenChange={setOpenEditModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar actuación</DialogTitle>
            <DialogDescription>
              Modifica la descripción de la actuación.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-action">Descripción</Label>
              <Textarea
                id="edit-action"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="Describe la actuación realizada..."
                rows={3}
                onKeyDown={(e) => e.key === 'Enter' && e.ctrlKey && handleUpdateAction()}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenEditModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleUpdateAction} disabled={actionLoading || !editValue.trim()}>
              {actionLoading ? 'Guardando...' : 'Guardar cambios'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

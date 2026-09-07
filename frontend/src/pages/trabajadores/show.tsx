import { AuthenticatedLayout } from "@/layouts"
import { ChevronLeft, MapPin, Building2, CreditCard, CalendarCheck, CalendarX, Mail, Hash } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Main } from "@/components/layout"
import { Link, useNavigate } from "react-router-dom"
import { pathFor } from "@/lib/app-routes"
import { PageProps } from "@/types"

interface Trabajador {
  id: number
  synergy_res_id: number
  nombre_completo: string
  email: string | null
  loc: string | null
  ubicacion: string | null
  ciudad: string | null
  telefono_synergy: string | null
  imei: string | null
  telefonos_id: number | null
  emp_stat: string | null
  activo: boolean
  fecha_alta: string | null
  fecha_baja: string | null
  created_at: string
  updated_at: string
}

interface ShowTrabajadorPageProps extends PageProps {
  trabajador: Trabajador
}

const formatDate = (dateString?: string | null) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function InfoRow({ label, value }: { label: React.ReactNode; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-4 py-2.5">
      <span className="text-sm text-muted-foreground shrink-0">{label}</span>
      <span className="text-sm font-medium text-right">{value ?? '—'}</span>
    </div>
  )
}

export default function TrabajadorShow({ trabajador }: ShowTrabajadorPageProps) {
  const navigate = useNavigate()

  return (
    <AuthenticatedLayout title={trabajador.nombre_completo}>
      <Main>
        <div className="mx-auto max-w-4xl w-full flex flex-col gap-6">

            {/* Header */}
            <div className="flex items-center gap-4">
              <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => navigate(pathFor('admin.trabajadores.index'))}>
                <ChevronLeft className="h-4 w-4" />
                <span className="sr-only">Volver</span>
              </Button>
              <div className="flex flex-1 items-center gap-3 min-w-0">
                <h1 className="text-xl font-semibold tracking-tight truncate">
                  {trabajador.nombre_completo}
                </h1>
                <Badge variant={trabajador.activo ? 'default' : 'secondary'}>
                  {trabajador.activo ? 'Activo' : 'Baja'}
                </Badge>
              </div>
              <span className="hidden sm:inline text-sm text-muted-foreground font-mono">
                SYR-{trabajador.synergy_res_id}
              </span>
            </div>

            {/* Content grid */}
            <div className="grid gap-4 md:grid-cols-[1fr_300px] lg:gap-8">

              {/* Left column */}
              <div className="grid auto-rows-max items-start gap-4 lg:gap-8">

                {/* Datos personales */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Datos personales</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InfoRow label="Nombre completo" value={trabajador.nombre_completo} />
                    <Separator />
                    <InfoRow
                      label="Email"
                      value={
                        trabajador.email
                          ? <a href={`mailto:${trabajador.email}`} className="text-primary hover:underline">{trabajador.email}</a>
                          : '—'
                      }
                    />
                    <Separator />
                    <InfoRow label="IMEI" value={trabajador.imei ?? '—'} />
                    <Separator />
                    <InfoRow label="Estado Synergy" value={trabajador.emp_stat ?? '—'} />
                  </CardContent>
                </Card>

                {/* Localización */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      Localización
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InfoRow label="Ubicación" value={trabajador.ubicacion?.trim()} />
                    <Separator />
                    <InfoRow label="Ciudad" value={trabajador.ciudad} />
                    <Separator />
                    <InfoRow label="Código LOC" value={trabajador.loc?.trim() || '—'} />
                  </CardContent>
                </Card>

              </div>

              {/* Right column */}
              <div className="grid auto-rows-max items-start gap-4 lg:gap-8">

                {/* Organización */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      Contacto
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InfoRow
                      label="Teléfono"
                      value={
                        trabajador.telefono_synergy && trabajador.telefonos_id
                          ? <Link to={pathFor('admin.telefonos.show', trabajador.telefonos_id)} className="font-mono text-primary hover:underline">{trabajador.telefono_synergy}</Link>
                          : (trabajador.telefono_synergy ?? '—')
                      }
                    />
                    <Separator />
                    <InfoRow
                      label="Email"
                      value={
                        trabajador.email
                          ? <span className="text-primary">{trabajador.email}</span>
                          : '—'
                      }
                    />
                  </CardContent>
                </Card>

                {/* Fechas */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Fechas</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InfoRow
                      label={
                        <span className="flex items-center gap-1.5">
                          <CalendarCheck className="h-3.5 w-3.5" />
                          Alta
                        </span>
                      }
                      value={formatDate(trabajador.fecha_alta)}
                    />
                    {!trabajador.activo && (
                      <>
                        <Separator />
                        <InfoRow
                          label={
                            <span className="flex items-center gap-1.5 text-destructive">
                              <CalendarX className="h-3.5 w-3.5" />
                              Baja
                            </span>
                          }
                          value={<span className="text-destructive">{formatDate(trabajador.fecha_baja)}</span>}
                        />
                      </>
                    )}
                  </CardContent>
                </Card>

                {/* Identificadores */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Hash className="h-4 w-4 text-muted-foreground" />
                      Identificadores
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InfoRow label="ID interno" value={<span className="font-mono">{trabajador.id}</span>} />
                    <Separator />
                    <InfoRow label="Synergy RES ID" value={<span className="font-mono">{trabajador.synergy_res_id}</span>} />
                    <Separator />
                    <InfoRow label="IMEI" value={trabajador.imei ?? '—'} />
                  </CardContent>
                </Card>

              </div>
            </div>

        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

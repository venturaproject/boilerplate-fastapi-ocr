import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AuthenticatedLayout } from '@/layouts'
import { Main } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { DevicePhonesTable } from '@/components/device-phones-table'
import { DeviceEmployeesTable } from '@/components/device-employees-table'
import { useI18n } from '@/i18n/context'
import { pathFor } from '@/lib/app-routes'
import { dispositivosApi } from '@/services/dispositivos-api'
import { BrandOptions, Dispositivo, ModelOptions, TrabajadorOption, TypeOptions, AssociatedPhone, AssociatedEmployee } from './types'
import { TrabajadorSelect } from '@/components/trabajador-select'
import { PhoneLineSelect, type PhoneOption } from '@/components/phone-line-select'
import { toast } from 'sonner'

// IMEI: exactly 15 digits, Luhn check on frontend
const isValidImei = (val: string): boolean => {
  if (!/^\d{15}$/.test(val)) return false
  let sum = 0
  let alt = false
  for (let i = val.length - 1; i >= 0; i--) {
    let d = parseInt(val[i], 10)
    if (alt) {
      d *= 2
      if (d > 9) d -= 9
    }
    sum += d
    alt = !alt
  }
  return sum % 10 === 0
}

const deviceSchema = z.object({
  marca: z.string().max(100).optional().or(z.literal('')),
  modelo: z.string().max(100).optional().or(z.literal('')),
  imei: z.string().optional().or(z.literal('')).refine(
    (v) => !v || v === '' || isValidImei(v),
    { message: 'El IMEI debe tener exactamente 15 dígitos y ser válido.' }
  ),
  numero: z.string().max(50).optional().or(z.literal('')),
  grupo: z.string().max(100).optional().or(z.literal('')),
  otros: z.string().optional().or(z.literal('')),
  employee_synergy_res_id: z.coerce.number().int().min(1).optional().or(z.literal(null)),
})

type DeviceFormValues = z.infer<typeof deviceSchema>

interface DispositivoEditProps {
  device: Dispositivo
  selectedBrand?: string | null
  selectedGrupo?: string | null
  brandOptions?: BrandOptions
  typeOptions?: TypeOptions
  trabajadorOptions?: TrabajadorOption[]
  workerPhone?: string | null
  workerPhoneId?: number | null
  phoneOptions?: PhoneOption[]
  associatedPhones?: AssociatedPhone[]
  associatedEmployees?: AssociatedEmployee[]
}

export default function DispositivoEdit({
  device,
  selectedBrand = null,
  selectedGrupo = null,
  brandOptions = {},
  typeOptions = {},
  trabajadorOptions = [],
  workerPhone = null,
  workerPhoneId = null,
  phoneOptions = [],
  associatedPhones = [],
  associatedEmployees = [],
}: DispositivoEditProps) {
  const { t } = useI18n()
  const navigate = useNavigate()

  const [modelOptions, setModelOptions] = useState<ModelOptions>({})
  const isFetchingModels = useRef(false)

  const form = useForm<DeviceFormValues>({
    resolver: zodResolver(deviceSchema),
    defaultValues: {
      marca: selectedBrand ?? device.marca ?? '',
      modelo: device.modelo ?? '',
      imei: device.imei ?? '',
      numero: device.numero || workerPhone || '',
      grupo: selectedGrupo ?? device.grupo ?? '',
      otros: device.otros ?? '',
      employee_synergy_res_id: device.employee_synergy_res_id ?? null,
    },
  })

  const watchedBrand = form.watch('marca')

  useEffect(() => {
    if (!watchedBrand) {
      setModelOptions({})
      form.setValue('modelo', '')
      return
    }

    const fetchModels = async () => {
      if (isFetchingModels.current) return
      isFetchingModels.current = true

      try {
        const data = await dispositivosApi.modelOptions(watchedBrand)
        if (device.modelo && !data[device.modelo]) {
          data[device.modelo] = device.modelo
        }
        setModelOptions(data)
      } catch {
        setModelOptions({})
      } finally {
        isFetchingModels.current = false
      }
    }

    fetchModels()
  }, [watchedBrand])

  const onSubmit = (data: DeviceFormValues) => {
    dispositivosApi.update(device.id, data)
      .then(() => {
        toast.success(t('device_updated'))
      })
      .catch(() => {
        toast.error(t('please_try_again'))
      })
  }

  const { formState: { isSubmitting } } = form

  return (
    <AuthenticatedLayout title={t('dispositivos_title')}>
      <Main>
        <div className="flex-1 space-y-6">
          {/* Header con Botones Estandarizados */}
          <div className="flex items-center justify-between">
            <div className="flex-1 space-y-1">
              <h1 className="text-2xl font-bold tracking-tight">
                {t('edit_device_title', { id: device.id })}
              </h1>
              <p className="text-muted-foreground">{device.marca} {device.modelo}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => navigate(pathFor('admin.dispositivos.show', device.id))}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t('back')}
              </Button>
              <Button type="submit" form="device-form" disabled={isSubmitting}>
                <Save className="mr-2 h-4 w-4" />
                {isSubmitting ? 'Guardando...' : t('save_changes')}
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t('device_form_title')}</CardTitle>
              <CardDescription>{t('device_form_description')}</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form id="device-form" onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <div className="grid gap-6 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="marca"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_marca')}</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value ?? ''}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder={t('select_marca')} />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {Object.entries(brandOptions).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                  {label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="modelo"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_modelo')}</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value ?? ''}
                            disabled={!watchedBrand}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder={t('select_modelo')} />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {Object.entries(modelOptions).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                  {label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="grupo"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_grupo')}</FormLabel>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value ?? ''}
                          >
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder={t('select_grupo')} />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {Object.entries(typeOptions).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                  {label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="employee_synergy_res_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_trabajador')}</FormLabel>
                          <FormControl>
                            <TrabajadorSelect
                              value={field.value}
                              onChange={field.onChange}
                              options={trabajadorOptions}
                              placeholder={t('select_trabajador')}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="imei"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_imei')}</FormLabel>
                          <FormControl>
                            <Input {...field} placeholder={t('col_imei')} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="numero"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-2">
                            {t('col_linea')}
                            {workerPhone && workerPhoneId ? (
                              <Link
                                to={pathFor('admin.telefonos.show', workerPhoneId)}
                                className="font-mono text-xs text-primary hover:underline"
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {workerPhone} ↗
                              </Link>
                            ) : workerPhone ? (
                              <span className="font-mono text-xs text-muted-foreground">{workerPhone}</span>
                            ) : null}
                          </FormLabel>
                          <FormControl>
                            <PhoneLineSelect
                              value={field.value ?? ''}
                              onChange={field.onChange}
                              options={phoneOptions}
                              placeholder={t('select_linea')}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name="otros"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('col_otros')}</FormLabel>
                        <FormControl>
                          <Textarea
                            {...field}
                            value={field.value ?? ''}
                            placeholder={t('col_otros')}
                            rows={3}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>

        {/* Association Tabs (only phones and employees, no receipts on edit) */}
        {(associatedPhones.length > 0 || associatedEmployees.length > 0) && (
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
            </TabsList>

            <TabsContent value="phones">
              <DevicePhonesTable phones={associatedPhones} />
            </TabsContent>

            <TabsContent value="employees">
              <DeviceEmployeesTable employees={associatedEmployees} />
            </TabsContent>
          </Tabs>
        )}
      </Main>
    </AuthenticatedLayout>
  )
}

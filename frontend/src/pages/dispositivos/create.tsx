import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
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
import { useI18n } from '@/i18n/context'
import { useFlashToast } from '@/hooks/use-flash-toast'
import { pathFor } from '@/lib/app-routes'
import { dispositivosApi } from '@/services/dispositivos-api'
import { BrandOptions, ModelOptions, TrabajadorOption, TypeOptions } from './types'
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

interface DispositivoCreateProps {
  brandOptions?: BrandOptions
  typeOptions?: TypeOptions
  trabajadorOptions?: TrabajadorOption[]
  phoneOptions?: PhoneOption[]
}

export default function DispositivoCreate({
  brandOptions = {},
  typeOptions = {},
  trabajadorOptions = [],
  phoneOptions = [],
}: DispositivoCreateProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  useFlashToast()

  const [modelOptions, setModelOptions] = useState<ModelOptions>({})
  const isFetchingModels = useRef(false)

  const form = useForm<DeviceFormValues>({
    resolver: zodResolver(deviceSchema),
    defaultValues: {
      marca: '',
      modelo: '',
      imei: '',
      numero: '',
      grupo: '',
      otros: '',
      employee_synergy_res_id: null,
    },
  })

  const selectedBrand = form.watch('marca')

  useEffect(() => {
    if (!selectedBrand) {
      setModelOptions({})
      form.setValue('modelo', '')
      return
    }

    const fetchModels = async () => {
      if (isFetchingModels.current) return
      isFetchingModels.current = true

      try {
        const data = await dispositivosApi.modelOptions(selectedBrand)
        setModelOptions(data)
      } catch {
        setModelOptions({})
      } finally {
        isFetchingModels.current = false
      }
    }

    fetchModels()
  }, [selectedBrand])

  const onSubmit = (data: DeviceFormValues) => {
    dispositivosApi.create(data)
      .then((response) => {
        toast.success(t('device_created'))
        const createdId = response?.id
        navigate(createdId ? pathFor('admin.dispositivos.show', createdId) : pathFor('admin.dispositivos.index'))
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
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(pathFor('admin.dispositivos.index'))}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{t('create_device_title')}</h1>
              <p className="text-muted-foreground">{t('create_device_description')}</p>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t('device_form_title')}</CardTitle>
              <CardDescription>{t('device_form_description')}</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <div className="grid gap-6 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="marca"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('col_marca')}</FormLabel>
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                            defaultValue={field.value}
                            disabled={!selectedBrand}
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
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                          <FormLabel>{t('col_linea')}</FormLabel>
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

                  <div className="mt-6 flex items-center gap-4">
                    <Button type="submit" disabled={isSubmitting}>
                      <Save className="mr-2 h-4 w-4" />
                      {isSubmitting ? 'Guardando...' : t('create_device')}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate(pathFor('admin.dispositivos.index'))}
                    >
                      {t('cancel')}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>
      </Main>
    </AuthenticatedLayout>
  )
}

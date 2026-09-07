import {
  IconBarrierBlock,
  IconBrowserCheck,
  IconBug,
  IconChecklist,
  IconError404,
  IconHelp,
  IconLayoutDashboard,
  IconLock,
  IconLockAccess,
  IconMessages,
  IconNotification,
  IconPackages,
  IconPalette,
  IconServerOff,
  IconSettings,
  IconTool,
  IconUserCog,
  IconUserOff,
  IconUsers,
  IconChartBar,
  IconPhone,
  IconMail,
  IconArticle,
  IconShield,
  IconKey,
  IconScan,
} from '@tabler/icons-react'
import {
  AudioWaveform,
  Command,
  GalleryVerticalEnd
} from 'lucide-react'
import { type SidebarData } from '../types'
import TradivelLogo from '../tradivel-logo'

export const sidebarData: SidebarData = {
  teams: [
    {
      name: 'Tradivel',
      logo: TradivelLogo,
      plan: 'Plataforma E-commerce',
    },
  ],
  navGroups: [
    {
      title: 'General',
      items: [
        {
          title: 'Dashboard',
          url: '/admin',
          icon: IconLayoutDashboard,
        },
      ],
    },
    {
      title: 'OCR',
      items: [
        {
          title: 'Reconocer',
          url: '/admin/ocr',
          icon: IconScan,
          permission: 'ocr.use',
        },
        {
          title: 'Trabajos',
          url: '/admin/ocr/jobs',
          icon: IconChecklist,
          permission: 'ocr.jobs.view',
        },
      ],
    },
    {
      title: 'Recursos Humanos',
      items: [
        {
          title: 'Trabajadores',
          url: '/admin/trabajadores',
          icon: IconUsers,
        },
        {
          title: 'Teléfonos',
          url: '/admin/telefonos',
          icon: IconPhone,
        },
      ],
    },
    {
      title: 'Control de Acceso',
      items: [
        {
          title: 'Usuarios',
          url: '/admin/users',
          icon: IconUsers,
          permission: 'users.view',
        },
        {
          title: 'Roles',
          url: '/admin/roles',
          icon: IconShield,
          permission: 'roles.view',
        },
        {
          title: 'Permisos',
          url: '/admin/permissions',
          icon: IconKey,
          permission: 'permissions.view',
        },
      ],
    },
    {
      title: 'Otros',
      items: [
        {
          title: 'Configuración',
          icon: IconSettings,
          items: [
            {
              title: 'Perfil',
              url: '/admin/settings',
              icon: IconUserCog,
            },
            {
              title: 'Cuenta',
              url: '/admin/settings/account',
              icon: IconTool,
            },
            {
              title: 'Apariencia',
              url: '/admin/settings/appearance',
              icon: IconPalette,
            },
            {
              title: 'Notificaciones',
              url: '/admin/settings/notifications',
              icon: IconNotification,
            },
            {
              title: 'Visualización',
              url: '/admin/settings/display',
              icon: IconBrowserCheck,
            },
          ],
        },
        {
          title: 'Centro de Ayuda',
          url: '/admin/help-center',
          icon: IconHelp,
        },
      ],
    },
  ],
}

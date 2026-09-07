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
  IconUserCog,
  IconUserOff,
  IconUsers,
  IconChartBar,
  IconMail,
  IconArticle,
  IconScan,
  IconListDetails,
  IconFileText,
} from '@tabler/icons-react'
import {
  AudioWaveform,
  Command,
  GalleryVerticalEnd
} from 'lucide-react'
import { type SidebarData } from '../types'
import TradivelLogo from '../tradivel-logo'
import { useI18n } from '@/i18n/context'

export const DynamicSidebarData = () => {
  const { t } = useI18n()

  const sidebarData: SidebarData = {
    teams: [
      {
        name: 'Tradivel',
        logo: TradivelLogo,
        plan: 'OCR API',
      },
    ],
    navGroups: [
      {
        title: t('general'),
        items: [
          {
            title: t('dashboard'),
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
            icon: IconListDetails,
            permission: 'ocr.jobs.view',
          },
          {
            title: 'Documentos',
            url: '/admin/documents',
            icon: IconFileText,
            permission: 'documents.view',
          },
        ],
      },
      {
        title: t('access_control'),
        items: [
          {
            title: t('users'),
            url: '/admin/users',
            icon: IconUsers,
            permission: 'users.view',
          },
        ],
      },
      {
        title: t('others'),
        items: [
          {
            title: t('configuration'),
            icon: IconSettings,
            items: [
              {
                title: t('profile'),
                url: '/admin/settings',
                icon: IconUserCog,
              },
              {
                title: t('appearance'),
                url: '/admin/settings/appearance',
                icon: IconPalette,
              },
              {
                title: t('notifications'),
                url: '/admin/settings/notifications',
                icon: IconNotification,
              },
              {
                title: t('display'),
                url: '/admin/settings/display',
                icon: IconBrowserCheck,
              },
            ],
          },
          {
            title: t('help_center'),
            url: '/admin/help-center',
            icon: IconHelp,
          },
        ],
      },
    ],
  };

  return sidebarData;
};
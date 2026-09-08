/**
 * Application route registry.
 *
 * This is the only file that should need to change when adding, removing,
 * or renaming business-module routes. The core router (lib/router.tsx) has
 * no knowledge of these paths.
 */
import type { RouteObject } from 'react-router-dom'

// Auth pages
import SignIn from '@/pages/auth/sign-in/sign-in-2'
import ForgotPasswordPage from '@/pages/auth/forgot-password'

// Route wrappers (each wraps one or more pages for a domain module)
import DashboardRoute from '@/routes/dashboard-route'
import UsersRoute from '@/routes/users-route'
import RolesRoute from '@/routes/roles-route'
import PermissionsRoute from '@/routes/permissions-route'
import SettingsRoute from '@/routes/settings-route'
import OcrRoute from '@/routes/ocr-route'
import DocumentsRoute from '@/routes/documents-route'
import AuditRoute from '@/routes/audit-route'

// ── Guest routes (unauthenticated only) ───────────────────────────────────────

export const guestRoutes: RouteObject[] = [
  { path: '/login', element: <SignIn canResetPassword={true} /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
]

// ── Private routes (authenticated only) ──────────────────────────────────────

export const privateRoutes: RouteObject[] = [
  // Dashboard
  { path: '/admin', element: <DashboardRoute /> },

  // OCR module
  { path: '/admin/ocr', element: <OcrRoute /> },
  { path: '/admin/ocr/jobs', element: <OcrRoute /> },
  { path: '/admin/ocr/jobs/:id', element: <OcrRoute /> },

  // Documents module (OCR processing registry)
  { path: '/admin/documents', element: <DocumentsRoute /> },
  { path: '/admin/documents/:id', element: <DocumentsRoute /> },

  // Security audit log
  { path: '/admin/audit', element: <AuditRoute /> },

  // Users module
  { path: '/admin/users', element: <UsersRoute /> },
  { path: '/admin/users/create', element: <UsersRoute /> },
  { path: '/admin/users/:id', element: <UsersRoute /> },
  { path: '/admin/users/:id/edit', element: <UsersRoute /> },

  // Roles module
  { path: '/admin/roles', element: <RolesRoute /> },
  { path: '/admin/roles/create', element: <RolesRoute /> },
  { path: '/admin/roles/:id/edit', element: <RolesRoute /> },

  // Permissions module
  { path: '/admin/permissions', element: <PermissionsRoute /> },
  { path: '/admin/permissions/create', element: <PermissionsRoute /> },
  { path: '/admin/permissions/:id/edit', element: <PermissionsRoute /> },

  // Settings
  { path: '/admin/settings', element: <SettingsRoute /> },
  { path: '/admin/settings/:section', element: <SettingsRoute /> },
]

type RouteParams = Record<string, any> | string | number | null | undefined
type RouteValue = string | ((params: Record<string, any>) => string)

export const appRouteMap: Record<string, RouteValue> = {
  login: '/login',
  logout: '/logout',
  'password.request': '/forgot-password',
  'password.reset': (p) => `/reset-password/${p.token}`,
  'verification.notice': '/verify-email',
  'password.confirm': '/confirm-password',

  dashboard: '/admin',

  'profile.edit': '/admin/settings',
  'profile.update': '/api/v1/auth/me',
  'profile.destroy': '/api/v1/auth/me',
  'profile.avatar.update': '/api/v1/auth/me/avatar',
  'dashboard.settings.profile': '/admin/settings',
  'dashboard.settings.permissions': '/admin/settings/permissions',
  'dashboard.settings.appearance': '/admin/settings/appearance',
  'dashboard.settings.appearance.update': '/admin/settings/appearance',
  'dashboard.settings.notifications': '/admin/settings/notifications',
  'dashboard.settings.notifications.update': '/admin/settings/notifications',
  'dashboard.settings.display': '/admin/settings/display',
  'dashboard.settings.display.update': '/admin/settings/display',
  'dashboard.settings.account': '/admin/settings/account',
  'dashboard.settings.avatar.update': '/admin/settings/avatar',

  'admin.users.index': '/admin/users',
  'admin.users.create': '/admin/users/create',
  'admin.users.store': '/admin/users',
  'admin.users.show': (p) => `/admin/users/${p.user ?? p.id}`,
  'admin.users.edit': (p) => `/admin/users/${p.user ?? p.id}/edit`,
  'admin.users.update': (p) => `/admin/users/${p.user ?? p.id}`,
  'admin.users.destroy': (p) => `/admin/users/${p.user ?? p.id}`,
  'admin.users.bulk-export': '/admin/users/bulk-export',

  'admin.roles.index': '/admin/roles',
  'admin.roles.create': '/admin/roles/create',
  'admin.roles.store': '/admin/roles',
  'admin.roles.edit': (p) => `/admin/roles/${p.role ?? p.id}/edit`,
  'admin.roles.update': (p) => `/admin/roles/${p.role ?? p.id}`,
  'admin.roles.destroy': (p) => `/admin/roles/${p.role ?? p.id}`,

  'admin.permissions.index': '/admin/permissions',
  'admin.permissions.create': '/admin/permissions/create',
  'admin.permissions.store': '/admin/permissions',
  'admin.permissions.edit': (p) => `/admin/permissions/${p.permission ?? p.id}/edit`,
  'admin.permissions.update': (p) => `/admin/permissions/${p.permission ?? p.id}`,
  'admin.permissions.destroy': (p) => `/admin/permissions/${p.permission ?? p.id}`,

  'admin.telefonos.index': '/admin/telefonos',
  'admin.telefonos.show': (p) => `/admin/telefonos/${p.id}`,
  'admin.telefonos.edit': (p) => `/admin/telefonos/${p.id}/edit`,
  'admin.telefonos.update': (p) => `/admin/telefonos/${p.id}`,
  'admin.telefonos.bulk-export': '/admin/telefonos/bulk-export',
  'admin.telefonos.bulk-desactivar': '/admin/telefonos/bulk-desactivar',
  'admin.telefonos.sync': '/admin/telefonos/sync',
  'admin.telefonos.desactivar': (p) => `/admin/telefonos/${p.id}/desactivar`,
  'admin.telefonos.actions.store': (p) => `/admin/telefonos/${p.id}/actuaciones`,
  'admin.telefonos.actions.update': (p) => `/admin/telefonos/actuaciones/${p.actionId}`,
  'admin.telefonos.actions.delete': (p) => `/admin/telefonos/actuaciones/${p.actionId}`,

  'api.device-models': (p) => `/api/v1/dispositivos/modelos/?brand=${encodeURIComponent(p.brand ?? '')}`,

  'admin.dispositivos.index': '/admin/dispositivos',
  'admin.dispositivos.create': '/admin/dispositivos/create',
  'admin.dispositivos.store': '/admin/dispositivos',
  'admin.dispositivos.show': (p) => `/admin/dispositivos/${p.id}`,
  'admin.dispositivos.edit': (p) => `/admin/dispositivos/${p.id}/edit`,
  'admin.dispositivos.update': (p) => `/admin/dispositivos/${p.id}`,
  'admin.dispositivos.bulk-export': '/admin/dispositivos/bulk-export',
  'admin.dispositivos.deliver': (p) => `/admin/dispositivos/${p.id}/deliver`,

  'admin.trabajadores.index': '/admin/trabajadores',
  'admin.trabajadores.show': (p) => `/admin/trabajadores/${p.id}`,
  'admin.trabajadores.bulk-export': '/admin/trabajadores/bulk-export',

  'admin.consulta-asistida.buscar': '/admin/consulta-asistida/buscar',
}

function normalizeParams(params?: RouteParams): Record<string, any> {
  if (params === null || params === undefined) return {}
  if (typeof params === 'object' && !Array.isArray(params)) return params
  return { id: params }
}

export function pathFor(name?: string, params?: RouteParams): string {
  if (!name) return window.location.pathname
  const entry = appRouteMap[name]
  if (!entry) {
    console.warn(`[pathFor] Unknown route name: "${name}"`)
    return '#'
  }
  return typeof entry === 'function' ? entry(normalizeParams(params)) : entry
}

pathFor.current = (name: string): boolean => {
  const target = pathFor(name)
  return window.location.pathname === target || window.location.pathname.startsWith(target + '/')
}

export default pathFor

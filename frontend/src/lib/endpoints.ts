// Central API endpoint registry — change the base path here to swap backends
const API_BASE = '/api/v1'

export const endpoints = {
  auth: {
    login:                    `${API_BASE}/auth/login`,
    logout:                   `${API_BASE}/auth/logout`,
    refresh:                  `${API_BASE}/auth/refresh`,
    me:                       `${API_BASE}/auth/me`,
    avatar:                   `${API_BASE}/auth/me/avatar`,
    forgotPassword:           `${API_BASE}/auth/forgot-password`,
    resetPassword:            `${API_BASE}/auth/reset-password`,
    verificationNotification: `${API_BASE}/auth/email/verification-notification`,
    csrf:                     `${API_BASE}/csrf/`,
  },
  users: {
    list:   `${API_BASE}/users`,
    detail: (id: string | number) => `${API_BASE}/users/${id}`,
  },
  roles: {
    list:   `${API_BASE}/roles`,
    detail: (id: string | number) => `${API_BASE}/roles/${id}`,
  },
  permissions: {
    list:   `${API_BASE}/permissions`,
    detail: (id: string | number) => `${API_BASE}/permissions/${id}`,
  },
  dashboard: `${API_BASE}/dashboard/`,
  notifications: {
    list:        `${API_BASE}/notifications`,
    detail:      (id: string | number) => `${API_BASE}/notifications/${id}`,
    markRead:    (id: string | number) => `${API_BASE}/notifications/${id}/read`,
    markAllRead: `${API_BASE}/notifications/read-all`,
  },
  upload: {
    presignedUrl: `${API_BASE}/upload/presigned-url`,
  },
  settings: {
    appearance:    `${API_BASE}/settings/appearance`,
    notifications: `${API_BASE}/settings/notifications`,
    display:       `${API_BASE}/settings/display`,
  },
  apiClients: {
    list:   `${API_BASE}/api-clients`,
    create: `${API_BASE}/api-clients`,
    revoke: (id: string) => `${API_BASE}/api-clients/${id}`,
  },
  ocr: {
    scan:      `${API_BASE}/ocr/scan`,
    classify:  `${API_BASE}/ocr/classify`,
    jobs:      `${API_BASE}/ocr/jobs`,
    jobDetail: (id: string) => `${API_BASE}/ocr/jobs/${id}`,
    stats:     `${API_BASE}/ocr/stats`,
  },
  documents: {
    list:   `${API_BASE}/documents`,
    detail: (id: string) => `${API_BASE}/documents/${id}`,
    stats:  `${API_BASE}/documents/stats`,
  },
}

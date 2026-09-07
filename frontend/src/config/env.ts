export const APP_URL = import.meta.env.VITE_APP_URL ?? ""

export const ASSET_URL = import.meta.env.VITE_ASSET_URL ?? ""

export const PUBLIC_API_URL = import.meta.env.VITE_PUBLIC_API_URL ?? ""

export const STORAGE_PREFIX = import.meta.env.VITE_STORAGE_PREFIX ?? "__ans_"

// Roles that bypass all permission checks. Set VITE_FULL_ACCESS_ROLES in .env
// to override (comma-separated). Defaults to "admin".
export const FULL_ACCESS_ROLES: string[] = (import.meta.env.VITE_FULL_ACCESS_ROLES ?? 'admin')
  .split(',')
  .map((r: string) => r.trim())
  .filter(Boolean)

export const env = {
  APP_URL,
  ASSET_URL,
  PUBLIC_API_URL,
  STORAGE_PREFIX,
  FULL_ACCESS_ROLES,
}
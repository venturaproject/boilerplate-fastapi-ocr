import { useEffect } from 'react'

export function DocumentTitle({ title }: { title?: string }) {
  useEffect(() => {
    const appName = (import.meta as any).env?.VITE_APP_NAME || 'App'
    document.title = title ? `${title} - ${appName}` : appName
  }, [title])

  return null
}

import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { Providers } from '@/providers'
import { ErrorBoundary } from '@/components/error-boundary'
import { createAppRouter } from '@/lib/router'
import { privateRoutes, guestRoutes } from '@/app-routes'

const router = createAppRouter({ privateRoutes, guestRoutes })

createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <Providers>
      <ErrorBoundary>
        <RouterProvider router={router} />
      </ErrorBoundary>
    </Providers>
  </StrictMode>,
)

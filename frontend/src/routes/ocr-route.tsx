import { useLocation } from 'react-router-dom'
import OcrPlayground from '@/pages/ocr/index'
import OcrJobs from '@/pages/ocr/jobs'

export default function OcrRoute() {
  const location = useLocation()
  if (location.pathname.startsWith('/admin/ocr/jobs')) {
    return <OcrJobs />
  }
  return <OcrPlayground />
}

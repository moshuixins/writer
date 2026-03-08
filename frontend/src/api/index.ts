import axios from 'axios'
import { toast } from 'vue-sonner'

const MAX_RETRY_COUNT = 3
const RETRY_DELAY = 1000

declare module 'axios' {
  export interface AxiosRequestConfig {
    retry?: boolean
    retryCount?: number
    skipErrorToast?: boolean
  }
}

const api = axios.create({
  baseURL: (import.meta.env.DEV && import.meta.env.VITE_OPEN_PROXY) ? '/proxy/' : import.meta.env.VITE_APP_API_BASEURL,
  timeout: 1000 * 60,
  responseType: 'json',
})

api.interceptors.request.use((request) => {
  const userStore = useUserStore()
  if (request.headers && userStore.isLogin) {
    request.headers.Authorization = `Bearer ${userStore.token}`
  }
  return request
})

export function resolveApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const baseURL = `${api.defaults.baseURL || ''}`.trim()
  if (!baseURL || baseURL === '/') {
    return normalizedPath
  }
  return `${baseURL.replace(/\/+$/, '')}${normalizedPath}`
}

async function normalizeBlobErrorPayload(error: any) {
  const data = error?.response?.data
  if (typeof Blob === 'undefined' || !(data instanceof Blob)) {
    return
  }

  const blobType = String(data.type || '')
  if (blobType && !blobType.includes('json') && !blobType.startsWith('text/')) {
    return
  }

  try {
    const rawText = await data.text()
    const text = rawText.trim()
    if (!text) {
      return
    }
    try {
      error.response.data = JSON.parse(text)
    }
    catch {
      error.response.data = { error: text }
    }
  }
  catch {
    // keep original error payload when blob parsing fails
  }
}

export function extractApiErrorMessage(error: any): string {
  const status = error.response?.status ?? error.status
  const payload = error.response?.data || {}
  const backendMessage = payload?.error || payload?.detail || ''
  const errorId = payload?.error_id

  if (status >= 500) {
    return errorId ? `服务器异常，请稍后重试（错误ID: ${errorId}）` : '服务器异常，请稍后重试'
  }

  if (backendMessage) {
    return String(backendMessage)
  }

  const fallback = String(error.message || '')
  if (fallback === 'Network Error') {
    return '后端网络故障'
  }
  if (fallback.toLowerCase().includes('timeout')) {
    return '接口请求超时'
  }
  return '请求失败，请稍后重试'
}

async function handleError(error: any) {
  await normalizeBlobErrorPayload(error)

  const status = error.response?.status ?? error.status
  const url = error.config?.url || ''
  const isAuthEndpoint = url.includes('/api/auth/login') || url.includes('/api/auth/register')

  if (status === 401 && !isAuthEndpoint) {
    useUserStore().requestLogout()
  }
  else if (!error.config?.skipErrorToast) {
    toast.error('请求失败', {
      description: extractApiErrorMessage(error),
    })
  }
  return Promise.reject(error)
}

api.interceptors.response.use(
  response => Promise.resolve(response),
  async (error) => {
    const config = error.config
    if (!config || !config.retry) {
      return handleError(error)
    }

    config.retryCount = config.retryCount || 0
    if (config.retryCount >= MAX_RETRY_COUNT) {
      return handleError(error)
    }

    config.retryCount += 1
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
    return api(config)
  },
)

export default api

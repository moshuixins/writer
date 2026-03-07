import type { AxiosRequestConfig } from 'axios'
import type { Preferences } from '@/types/writer'
import api from '../index'

export default {
  get: (config?: AxiosRequestConfig) => api.get<Preferences>('/api/preferences', config),

  save: (data: Preferences, config?: AxiosRequestConfig) => api.put('/api/preferences/batch', data, config),
}

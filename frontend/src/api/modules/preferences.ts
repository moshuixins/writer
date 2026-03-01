import api from '../index'
import type { AxiosRequestConfig } from 'axios'
import type { Preferences } from '@/types/writer'

export default {
  get: (config?: AxiosRequestConfig) => api.get<Preferences>('/api/preferences', config),

  save: (data: Preferences, config?: AxiosRequestConfig) => api.put('/api/preferences/batch', data, config),
}

import type { AxiosRequestConfig } from 'axios'
import type { MessageResponse, PreferencesResponse } from '../generated'
import type { Preferences } from '@/types/writer'
import api from '../index'

export default {
  get: (config?: AxiosRequestConfig) => api.get<PreferencesResponse>('/api/preferences', config),

  save: (data: Preferences, config?: AxiosRequestConfig) => api.put<MessageResponse>('/api/preferences/batch', data, config),
}

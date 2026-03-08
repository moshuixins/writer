import type { RecursiveRequired, Settings } from '#/global'
import { cloneDeep } from 'es-toolkit'
import settingsDefault from '@/settings.default'
import { merge } from '@/utils/object'

const globalSettings: Settings.all = {
  app: {
    enablePermission: false,
    enableDynamicTitle: true,
  },
  home: {
    enable: true,
    title: '写作会话',
    fullPath: '/chat',
  },
  menu: {
    mode: 'single',
    enableSubMenuCollapseButton: true,
  },
  copyright: {
    enable: false,
  },
}

export default merge(globalSettings, cloneDeep(settingsDefault)) as RecursiveRequired<Settings.all>

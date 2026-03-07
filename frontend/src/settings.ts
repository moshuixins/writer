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
    title: '\u516C\u6587\u5199\u4F5C\u52A9\u624B',
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

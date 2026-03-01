import type { RecursiveRequired, Settings } from '#/global'
import { cloneDeep } from 'es-toolkit'
import settingsDefault from '@/settings.default'
import { merge } from '@/utils/object'

const globalSettings: Settings.all = {
  app: {
    routeBaseOn: 'frontend',
    enablePermission: false,
    enableDynamicTitle: true,
  },
  home: {
    enable: true,
    title: '公文写作助手',
    fullPath: '/chat',
  },
  menu: {
    baseOn: 'frontend',
    mode: 'single',
    enableSubMenuCollapseButton: true,
  },
  toolbar: {
    breadcrumb: false,
    navSearch: false,
    fullscreen: false,
    colorScheme: true,
  },
  tabbar: {
    enable: false,
  },
  copyright: {
    enable: false,
  },
}

export default merge(globalSettings, cloneDeep(settingsDefault)) as RecursiveRequired<Settings.all>

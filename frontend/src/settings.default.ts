import type { RecursiveRequired, Settings } from '#/global'

const globalSettingsDefault: RecursiveRequired<Settings.all> = {
  app: {
    colorScheme: 'light',
    radius: 0.5,
    enableMournMode: false,
    enableColorAmblyopiaMode: false,
    enablePermission: false,
    enableProgress: true,
    enableDynamicTitle: false,
  },
  home: {
    enable: true,
    title: '\u4E3B\u9875',
    fullPath: '/',
  },
  layout: {
    enableMobileAdaptation: false,
  },
  menu: {
    mode: 'side',
    mainMenuClickMode: 'switch',
    subMenuUniqueOpened: true,
    subMenuCollapse: false,
    enableSubMenuCollapseButton: false,
  },
  copyright: {
    enable: false,
    dates: '',
    company: '',
    website: '',
    beian: '',
  },
}

export default globalSettingsDefault

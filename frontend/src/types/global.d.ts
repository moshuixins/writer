import type { RouteRecordRaw } from 'vue-router'

type RecursiveRequired<T> = {
  [P in keyof T]-?: RecursiveRequired<T[P]>
}
type RecursivePartial<T> = {
  [P in keyof T]?: RecursivePartial<T[P]>
}

declare namespace Settings {
  interface app {
    colorScheme?: 'light' | 'dark' | ''
    radius?: number
    enableMournMode?: boolean
    enableColorAmblyopiaMode?: boolean
    enablePermission?: boolean
    enableProgress?: boolean
    enableDynamicTitle?: boolean
  }

  interface home {
    enable?: boolean
    title?: string
    fullPath?: string
  }

  interface layout {
    enableMobileAdaptation?: boolean
  }

  interface menu {
    mode?: 'side' | 'head' | 'single'
    mainMenuClickMode?: 'switch' | 'jump' | 'smart'
    subMenuUniqueOpened?: boolean
    subMenuCollapse?: boolean
    enableSubMenuCollapseButton?: boolean
  }

  interface copyright {
    enable?: boolean
    dates?: string
    company?: string
    website?: string
    beian?: string
  }

  interface all {
    app?: app
    home?: home
    layout?: layout
    menu?: menu
    copyright?: copyright
  }
}

declare module 'vue-router' {
  interface RouteMeta {
    title?: string | (() => string)
    icon?: string
    defaultOpened?: boolean
    auth?: string | string[]
    menu?: boolean
    breadcrumb?: boolean
    cache?: boolean | string | string[]
    noCache?: string | string[]
    link?: string
  }
}

declare namespace Route {
  interface recordMainRaw {
    meta?: {
      title?: string | (() => string)
      icon?: string
      auth?: string | string[]
    }
    children: RouteRecordRaw[]
  }
}

declare namespace Menu {
  interface recordRaw {
    path?: string
    meta?: {
      title?: string | (() => string)
      icon?: string
      defaultOpened?: boolean
      auth?: string | string[]
      menu?: boolean
      link?: string
    }
    children?: recordRaw[]
  }

  interface recordMainRaw {
    meta?: {
      title?: string | (() => string)
      icon?: string
      auth?: string | string[]
    }
    children: recordRaw[]
  }
}

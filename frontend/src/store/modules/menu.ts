import type { Menu, Route } from '#/global'
import type { RouteRecordRaw } from 'vue-router'
import { cloneDeep } from 'es-toolkit'
import { resolveRoutePath } from '@/utils'
import { filterMenusByAuth } from '@/utils/permission'

export const useMenuStore = defineStore(
  'menu',
  () => {
    const settingsStore = useSettingsStore()
    const routeStore = useRouteStore()

    const actived = ref(0)

    function convertRouteToMenu(routes: Route.recordMainRaw[]): Menu.recordMainRaw[] {
      const result: Menu.recordMainRaw[] = []
      routes.forEach((item) => {
        if (item.children.length <= 0) {
          return
        }
        if (settingsStore.settings.menu.mode === 'single') {
          if (result.length === 0) {
            result.push({
              meta: {},
              children: [],
            })
          }
          result[0].children.push(...convertRouteToMenuRecursive(item.children))
          return
        }
        result.push({
          meta: {
            title: item.meta?.title,
            icon: item.meta?.icon,
            auth: item.meta?.auth,
          },
          children: convertRouteToMenuRecursive(item.children),
        })
      })
      return result
    }

    function convertRouteToMenuRecursive(routes: RouteRecordRaw[], basePath = ''): Menu.recordRaw[] {
      const result: Menu.recordRaw[] = []
      routes.forEach((item) => {
        const menuItem: Menu.recordRaw = {
          path: resolveRoutePath(basePath, item.path),
          meta: {
            title: item.meta?.title,
            icon: item.meta?.icon,
            defaultOpened: item.meta?.defaultOpened,
            auth: item.meta?.auth,
            menu: item.meta?.menu,
            link: item.meta?.link,
          },
        }
        if (item.children) {
          menuItem.children = convertRouteToMenuRecursive(item.children, menuItem.path)
        }
        result.push(menuItem)
      })
      return result
    }

    const auth = useAuth()
    function filterAsyncMenus<T extends Menu.recordMainRaw[] | Menu.recordRaw[]>(menus: T): T {
      return filterMenusByAuth(cloneDeep(menus) as any, auth.auth) as T
    }

    const allMenus = computed(() => {
      return filterAsyncMenus(convertRouteToMenu(routeStore.routesRaw))
    })

    const sidebarMenus = computed<Menu.recordMainRaw['children']>(() => {
      if (allMenus.value.length === 0) {
        return []
      }
      if (allMenus.value.length === 1) {
        return allMenus.value[0].children
      }
      return allMenus.value[actived.value].children
    })

    const sidebarMenusFirstDeepestPath = computed(() => {
      return sidebarMenus.value.length > 0
        ? getDeepestPath(sidebarMenus.value[0])
        : settingsStore.settings.home.fullPath
    })

    function getDeepestPath(menu: Menu.recordRaw, rootPath = ''): string {
      if (menu.children?.some(item => item.meta?.menu !== false)) {
        const item = menu.children.find(item => item.meta?.menu !== false) ?? menu.children[0]
        return getDeepestPath(item, resolveRoutePath(rootPath, menu.path))
      }
      return resolveRoutePath(rootPath, menu.path)
    }

    const sidebarMenusHasOnlyMenu = computed(() => {
      return isSidebarMenusHasOnlyMenu(sidebarMenus.value)
    })

    function isSidebarMenusHasOnlyMenu(menus: Menu.recordRaw[]): boolean {
      let count = 0
      let isOnly = true
      menus.forEach((menu) => {
        if (menu.meta?.menu !== false) {
          count++
        }
        if (menu.children) {
          isOnly = isSidebarMenusHasOnlyMenu(menu.children)
        }
      })
      return count <= 1 && isOnly
    }

    const defaultOpenedPaths = computed(() => {
      const result: string[] = []
      allMenus.value.forEach((item) => {
        result.push(...getDefaultOpenedPaths(item.children))
      })
      return result
    })

    function getDefaultOpenedPaths(menus: Menu.recordRaw[], rootPath = ''): string[] {
      const result: string[] = []
      menus.forEach((item) => {
        if (item.meta?.defaultOpened && item.children) {
          result.push(resolveRoutePath(rootPath, item.path))
          result.push(...getDefaultOpenedPaths(item.children, resolveRoutePath(rootPath, item.path)))
        }
      })
      return result
    }

    function isPathInMenus(menus: Menu.recordRaw[], path: string): boolean {
      return menus.some((item) => {
        if (item.children) {
          return isPathInMenus(item.children, path)
        }
        return path.indexOf(`${item.path}/`) === 0 || path === item.path
      })
    }

    function setActived(indexOrPath: number | string) {
      if (typeof indexOrPath === 'number') {
        actived.value = indexOrPath
        return
      }
      const findIndex = allMenus.value.findIndex(item => isPathInMenus(item.children, indexOrPath))
      if (findIndex >= 0) {
        actived.value = findIndex
      }
    }

    return {
      actived,
      allMenus,
      sidebarMenus,
      sidebarMenusFirstDeepestPath,
      sidebarMenusHasOnlyMenu,
      defaultOpenedPaths,
      setActived,
    }
  },
)

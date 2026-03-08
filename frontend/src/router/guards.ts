import type { Router, RouteRecordRaw } from 'vue-router'
import { useNProgress } from '@vueuse/integrations/useNProgress'
import { findFirstAccessibleChildRoute } from '@/utils/permission'
import { asyncRoutes } from './routes'
import '@/assets/styles/nprogress.css'

const protectedRoutePatterns = [
  /^\/chat(?:\/\d+)?$/,
  /^\/materials$/,
  /^\/book-learning$/,
  /^\/history$/,
  /^\/settings$/,
  /^\/admin(?:\/.+)?$/,
]

function isProtectedEntry(path: string) {
  return protectedRoutePatterns.some(pattern => pattern.test(path))
}

function setupRoutes(router: Router) {
  router.beforeEach(async (to, _from, next) => {
    const settingsStore = useSettingsStore()
    const userStore = useUserStore()
    const routeStore = useRouteStore()
    const menuStore = useMenuStore()

    if (userStore.isLogin) {
      if (routeStore.isGenerate) {
        if (settingsStore.settings.menu.mode !== 'single') {
          menuStore.setActived(to.path)
        }

        if (to.name === 'login') {
          next({
            path: settingsStore.settings.home.fullPath,
            replace: true,
          })
          return
        }

        if (!settingsStore.settings.home.enable && to.fullPath === settingsStore.settings.home.fullPath) {
          if (menuStore.sidebarMenus.length > 0) {
            next({
              path: menuStore.sidebarMenusFirstDeepestPath,
              replace: true,
            })
            return
          }
        }

        next()
        return
      }

      try {
        await userStore.getPermissions()
        routeStore.generateRoutes(asyncRoutes)

        const removeRoutes: (() => void)[] = []
        routeStore.routes.forEach((route) => {
          if (!/^(?:https?:|mailto:|tel:)/.test(route.path)) {
            removeRoutes.push(router.addRoute(route as RouteRecordRaw))
          }
        })
        routeStore.systemRoutes.forEach((route) => {
          removeRoutes.push(router.addRoute(route as RouteRecordRaw))
        })
        routeStore.setCurrentRemoveRoutes(removeRoutes)
      }
      catch {
        userStore.logout()
        return
      }

      next({
        path: to.path,
        query: to.query,
        replace: true,
      })
      return
    }

    if (to.name === 'notFound' && isProtectedEntry(to.path)) {
      next({
        name: 'login',
        query: {
          redirect: to.fullPath !== settingsStore.settings.home.fullPath ? to.fullPath : undefined,
        },
        replace: true,
      })
      return
    }

    if (to.meta.public || to.name === 'login') {
      next()
      return
    }

    next({
      name: 'login',
      query: {
        redirect: to.fullPath !== settingsStore.settings.home.fullPath ? to.fullPath : undefined,
      },
    })
  })
}

function setupRedirectAuthChildrenRoute(router: Router) {
  router.beforeEach((to, _from, next) => {
    const { auth } = useAuth()
    const currentRoute = router.getRoutes().find(route => route.path === (to.matched.at(-1)?.path ?? ''))
    if (!currentRoute?.redirect) {
      const findAuthRoute = findFirstAccessibleChildRoute(currentRoute?.children, auth)
      if (findAuthRoute) {
        next(findAuthRoute)
        return
      }
    }
    next()
  })
}

function setupProgress(router: Router) {
  const { isLoading } = useNProgress()
  router.beforeEach((_to, _from, next) => {
    const settingsStore = useSettingsStore()
    if (settingsStore.settings.app.enableProgress) {
      isLoading.value = true
    }
    next()
  })
  router.afterEach(() => {
    const settingsStore = useSettingsStore()
    if (settingsStore.settings.app.enableProgress) {
      isLoading.value = false
    }
  })
}

function setupTitle(router: Router) {
  router.afterEach((to) => {
    const settingsStore = useSettingsStore()
    settingsStore.setTitle(to.matched.at(-1)?.meta?.title ?? to.meta.title)
  })
}

function setupKeepAlive(router: Router) {
  router.afterEach(async (to, from) => {
    const keepAliveStore = useKeepAliveStore()
    if (to.fullPath !== from.fullPath && to.meta.cache) {
      const componentName = to.matched.at(-1)?.components?.default.name
      if (componentName) {
        let shouldClearCache = false
        if (typeof to.meta.cache === 'boolean') {
          shouldClearCache = !to.meta.cache
        }
        else if (typeof to.meta.cache === 'string') {
          shouldClearCache = to.meta.cache !== from.name
        }
        else if (Array.isArray(to.meta.cache)) {
          shouldClearCache = !to.meta.cache.includes(from.name as string)
        }
        if (to.meta.noCache) {
          if (typeof to.meta.noCache === 'string') {
            shouldClearCache = to.meta.noCache === from.name
          }
          else if (Array.isArray(to.meta.noCache)) {
            shouldClearCache = to.meta.noCache.includes(from.name as string)
          }
        }
        if (from.name === 'reload') {
          shouldClearCache = true
        }
        if (shouldClearCache) {
          keepAliveStore.remove(componentName)
          await nextTick()
        }
        keepAliveStore.add(componentName)
      }
      else {
        console.warn('[router] route component is missing a name, keep-alive may not work as expected')
      }
    }
  })
}

function setupOther(router: Router) {
  router.afterEach(() => {
    document.documentElement.scrollTop = 0
  })
}

export default function setupGuards(router: Router) {
  setupRoutes(router)
  setupRedirectAuthChildrenRoute(router)
  setupProgress(router)
  setupTitle(router)
  setupKeepAlive(router)
  setupOther(router)
}

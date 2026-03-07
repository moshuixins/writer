import type { Route } from '#/global'
import type { RouteRecordRaw } from 'vue-router'
import { cloneDeep } from 'es-toolkit'
import { systemRoutes as systemRoutesRaw } from '@/router/routes'

function deleteMiddleRouteComponent(routes: RouteRecordRaw[]) {
  const result: RouteRecordRaw[] = []
  routes.forEach((route) => {
    if (route.children?.length) {
      delete route.component
      route.children = deleteMiddleRouteComponent(route.children)
    }
    else {
      delete route.children
    }
    result.push(route)
  })
  return result
}

function normalizeRoutes(routesRaw: Route.recordMainRaw[]) {
  const result: RouteRecordRaw[] = []
  routesRaw.forEach((item) => {
    const children = cloneDeep(item.children) as RouteRecordRaw[]
    children.forEach((route) => {
      route.meta = {
        ...route.meta,
        auth: item.meta?.auth ?? route.meta?.auth,
      }
      if (route.children) {
        route.children = deleteMiddleRouteComponent(route.children)
      }
    })
    result.push(...children)
  })
  return result
}

export const useRouteStore = defineStore(
  'route',
  () => {
    const isGenerate = ref(false)
    const routesRaw = ref<Route.recordMainRaw[]>([])
    const currentRemoveRoutes = ref<(() => void)[]>([])

    const routes = computed(() => normalizeRoutes(routesRaw.value))
    const systemRoutes = computed(() => deleteMiddleRouteComponent(cloneDeep(systemRoutesRaw) as RouteRecordRaw[]))

    function generateRoutes(asyncRoutes: Route.recordMainRaw[]) {
      routesRaw.value = cloneDeep(asyncRoutes) as Route.recordMainRaw[]
      isGenerate.value = true
    }

    function setCurrentRemoveRoutes(routes: (() => void)[]) {
      currentRemoveRoutes.value = routes
    }

    function removeRoutes() {
      isGenerate.value = false
      routesRaw.value = []
      currentRemoveRoutes.value.forEach((removeRoute) => {
        removeRoute()
      })
      currentRemoveRoutes.value = []
    }

    return {
      isGenerate,
      routesRaw,
      currentRemoveRoutes,
      routes,
      systemRoutes,
      generateRoutes,
      setCurrentRemoveRoutes,
      removeRoutes,
    }
  },
)

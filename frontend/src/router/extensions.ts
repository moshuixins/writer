import type { NavigationFailure, RouteLocationRaw, Router } from 'vue-router'

declare module 'vue-router' {
  interface Router {
    close: (to: RouteLocationRaw) => Promise<NavigationFailure | void | undefined>
  }
}

function extendClose(router: Router) {
  router.close = function (to: RouteLocationRaw) {
    return router.push(to)
  }
}

export default function setupExtensions(router: Router) {
  extendClose(router)
}

import type { Route } from '#/global'
import type { RouteRecordRaw } from 'vue-router'
import generatedRoutes from 'virtual:generated-pages'
import { setupLayouts } from 'virtual:meta-layouts'
import Admin from './modules/admin'
import Writer from './modules/writer'

// ??????????
const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue'),
    meta: {
      title: '??',
    },
  },
  {
    path: '/:all(.*)*',
    name: 'notFound',
    component: () => import('@/views/[...all].vue'),
    meta: {
      title: '?????',
    },
  },
]

// ????
const systemRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat',
    component: () => import('@/layouts/index.vue'),
    meta: {
      title: () => useSettingsStore().settings.home.title,
      breadcrumb: false,
    },
    children: [
      {
        path: 'reload',
        name: 'reload',
        component: () => import('@/views/reload.vue'),
        meta: {
          title: '????',
          breadcrumb: false,
        },
      },
    ],
  },
]

// ????????????????
const asyncRoutes: Route.recordMainRaw[] = [
  {
    meta: {
      title: '????',
      icon: 'i-ep:edit-pen',
    },
    children: [
      Writer,
    ],
  },
  {
    meta: {
      title: '????',
      icon: 'i-ep:setting',
    },
    children: [
      Admin,
    ],
  },
]

const constantRoutesByFilesystem = generatedRoutes.filter((item) => {
  return item.meta?.enabled !== false && item.meta?.constant === true
})

const asyncRoutesByFilesystem = [...setupLayouts(generatedRoutes.filter((item) => {
  return item.meta?.enabled !== false && item.meta?.constant !== true && item.meta?.layout !== false
}))]

export {
  asyncRoutes,
  asyncRoutesByFilesystem,
  constantRoutes,
  constantRoutesByFilesystem,
  systemRoutes,
}

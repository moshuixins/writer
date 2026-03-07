import type { Route } from '#/global'
import type { RouteRecordRaw } from 'vue-router'
import Admin from './modules/admin'
import Writer from './modules/writer'

const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue'),
    meta: {
      title: '\u767B\u5F55',
    },
  },
  {
    path: '/:all(.*)*',
    name: 'notFound',
    component: () => import('@/views/[...all].vue'),
    meta: {
      title: '\u627E\u4E0D\u5230\u9875\u9762',
    },
  },
]

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
          title: '\u5237\u65B0\u9875\u9762',
          breadcrumb: false,
        },
      },
    ],
  },
]

const asyncRoutes: Route.recordMainRaw[] = [
  {
    meta: {
      title: '\u5199\u4F5C\u5DE5\u4F5C\u533A',
      icon: 'i-ep:edit-pen',
    },
    children: [Writer],
  },
  {
    meta: {
      title: '\u7CFB\u7EDF\u7BA1\u7406',
      icon: 'i-ep:setting',
    },
    children: [Admin],
  },
]

export {
  asyncRoutes,
  constantRoutes,
  systemRoutes,
}

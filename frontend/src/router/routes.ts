import type { Route } from '#/global'
import type { RouteRecordRaw } from 'vue-router'
import Admin from './modules/admin'
import Writer from './modules/writer'

const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: () => import('@/views/landing.vue'),
    meta: {
      title: '正式公文写作平台',
      public: true,
    },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue'),
    meta: {
      title: '登录',
      public: true,
    },
  },
  {
    path: '/:all(.*)*',
    name: 'notFound',
    component: () => import('@/views/[...all].vue'),
    meta: {
      title: '找不到页面',
      public: true,
    },
  },
]

const systemRoutes: RouteRecordRaw[] = [
  {
    path: '/reload',
    name: 'reload',
    component: () => import('@/views/reload.vue'),
    meta: {
      title: '刷新页面',
      breadcrumb: false,
    },
  },
]

const asyncRoutes: Route.recordMainRaw[] = [
  {
    meta: {
      title: '写作工作区',
      icon: 'i-ep:edit-pen',
    },
    children: [Writer],
  },
  {
    meta: {
      title: '系统管理',
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

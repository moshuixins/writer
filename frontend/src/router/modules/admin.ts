import type { RouteRecordRaw } from 'vue-router'

function Layout() {
  return import('@/layouts/index.vue')
}

const routes: RouteRecordRaw = {
  path: '/admin',
  component: Layout,
  name: 'admin',
  meta: {
    title: '管理后台',
    icon: 'i-ep:setting',
  },
  children: [
    {
      path: '/admin/overview',
      name: 'adminOverview',
      component: () => import('@/views/admin/AdminOverview.vue'),
      meta: {
        title: '概览',
        icon: 'i-ep:monitor',
        auth: 'accounts:read',
      },
    },
    {
      path: '/admin/accounts',
      name: 'adminAccounts',
      component: () => import('@/views/admin/AdminAccounts.vue'),
      meta: {
        title: '账户管理',
        icon: 'i-ep:office-building',
        auth: 'accounts:read',
      },
    },
    {
      path: '/admin/roles',
      name: 'adminRoles',
      component: () => import('@/views/admin/AdminRoles.vue'),
      meta: {
        title: '角色与权限',
        icon: 'i-ep:key',
        auth: 'accounts:read',
      },
    },
  ],
}

export default routes

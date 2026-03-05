import type { RouteRecordRaw } from 'vue-router'

function Layout() {
  return import('@/layouts/index.vue')
}

const routes: RouteRecordRaw = {
  path: '/admin',
  component: Layout,
  name: 'admin',
  meta: {
    title: 'Admin',
    icon: 'i-ep:setting',
  },
  children: [
    {
      path: '/admin/overview',
      name: 'adminOverview',
      component: () => import('@/views/admin/AdminOverview.vue'),
      meta: {
        title: 'Overview',
        icon: 'i-ep:monitor',
        auth: 'accounts:read',
      },
    },
    {
      path: '/admin/accounts',
      name: 'adminAccounts',
      component: () => import('@/views/admin/AdminAccounts.vue'),
      meta: {
        title: 'Accounts',
        icon: 'i-ep:office-building',
        auth: 'accounts:read',
      },
    },
    {
      path: '/admin/roles',
      name: 'adminRoles',
      component: () => import('@/views/admin/AdminRoles.vue'),
      meta: {
        title: 'Roles & Permissions',
        icon: 'i-ep:key',
        auth: 'accounts:read',
      },
    },
  ],
}

export default routes

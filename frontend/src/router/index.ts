import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      redirect: '/materials',
    },
    {
      path: '/materials',
      name: 'Materials',
      component: () => import('../views/MaterialManager.vue'),
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('../views/WritingChat.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/Settings.vue'),
    },
    {
      path: '/history',
      name: 'History',
      component: () => import('../views/ExportHistory.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/NotFound.vue'),
      meta: { public: true },
    },
  ],
})

// 路由守卫：未登录跳转到登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta?.public && !token) {
    return { name: 'Login' }
  }
})

export default router

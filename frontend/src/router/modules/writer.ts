import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'

function Layout() {
  return import('@/layouts/index.vue')
}

function redirectLegacyChatQuery(to: RouteLocationNormalized) {
  const rawSessionId = Array.isArray(to.query.session_id) ? to.query.session_id[0] : to.query.session_id
  const sessionId = Number(rawSessionId)
  if (!Number.isFinite(sessionId) || sessionId <= 0) {
    return true
  }
  return {
    name: 'writerWorkspace',
    params: { sessionId },
    replace: true,
  }
}

const routes: RouteRecordRaw = {
  path: '/writer',
  component: Layout,
  name: 'writer',
  meta: {
    title: '公文写作',
    icon: 'i-ep:edit-pen',
  },
  children: [
    {
      path: '/chat',
      name: 'writerChat',
      component: () => import('@/views/writer/WritingSessionsHome.vue'),
      beforeEnter: to => redirectLegacyChatQuery(to),
      meta: {
        title: '写作会话',
        icon: 'i-ep:chat-dot-round',
      },
    },
    {
      path: '/chat/:sessionId(\d+)',
      name: 'writerWorkspace',
      component: () => import('@/views/writer/WritingWorkspace.vue'),
      meta: {
        title: '写作工作台',
        icon: 'i-ep:chat-dot-round',
      },
    },
    {
      path: '/materials',
      name: 'writerMaterials',
      component: () => import('@/views/writer/MaterialManager.vue'),
      meta: {
        title: '素材管理',
        icon: 'i-ep:document',
      },
    },
    {
      path: '/book-learning',
      name: 'writerBookLearning',
      component: () => import('@/views/writer/BookLearning.vue'),
      meta: {
        title: '书籍学习',
        icon: 'i-ep:reading',
      },
    },
    {
      path: '/history',
      name: 'writerHistory',
      component: () => import('@/views/writer/ExportHistory.vue'),
      meta: {
        title: '导出历史',
        icon: 'i-ep:folder-opened',
      },
    },
    {
      path: '/settings',
      name: 'writerSettings',
      component: () => import('@/views/writer/Settings.vue'),
      meta: {
        title: '写作偏好',
        icon: 'i-ep:setting',
      },
    },
  ],
}

export default routes

import type { RouteRecordRaw } from 'vue-router'

function Layout() {
  return import('@/layouts/index.vue')
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
      component: () => import('@/views/writer/WritingChat.vue'),
      meta: {
        title: '写作对话',
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
        title: '偏好设置',
        icon: 'i-ep:setting',
      },
    },
  ],
}

export default routes

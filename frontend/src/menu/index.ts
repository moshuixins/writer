import type { Menu } from '#/global'

const menu: Menu.recordMainRaw[] = [
  {
    meta: {
      title: '公文写作',
      icon: 'ep:edit-pen',
    },
    children: [
      {
        path: '/chat',
        meta: { title: '写作对话', icon: 'ep:chat-dot-round' },
      },
      {
        path: '/materials',
        meta: { title: '素材管理', icon: 'ep:document' },
      },
      {
        path: '/history',
        meta: { title: '导出历史', icon: 'ep:folder-opened' },
      },
      {
        path: '/settings',
        meta: { title: '偏好设置', icon: 'ep:setting' },
      },
    ],
  },
]

export default menu

export interface BusinessNavItem {
  key: string
  title: string
  path: string
  icon: string
  auth?: string | string[]
}

export interface BusinessNavGroup {
  key: string
  title: string
  items: BusinessNavItem[]
}

export const businessNavGroups: BusinessNavGroup[] = [
  {
    key: 'writer',
    title: '写作工作区',
    items: [
      { key: 'chat', title: '写作会话', path: '/chat', icon: 'i-ep:chat-dot-round' },
      { key: 'materials', title: '素材管理', path: '/materials', icon: 'i-ep:document' },
      { key: 'books', title: '书籍学习', path: '/book-learning', icon: 'i-ep:reading' },
      { key: 'history', title: '导出历史', path: '/history', icon: 'i-ep:folder-opened' },
      { key: 'settings', title: '写作偏好', path: '/settings', icon: 'i-ep:setting' },
    ],
  },
  {
    key: 'admin',
    title: '系统管理',
    items: [
      { key: 'adminOverview', title: '管理概览', path: '/admin/overview', icon: 'i-ep:monitor', auth: 'accounts:read' },
      { key: 'adminAccounts', title: '账户与用户', path: '/admin/accounts', icon: 'i-ep:office-building', auth: 'accounts:read' },
      { key: 'adminRoles', title: '角色与权限', path: '/admin/roles', icon: 'i-ep:key', auth: 'accounts:read' },
    ],
  },
]

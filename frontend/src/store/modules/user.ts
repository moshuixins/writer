import apiUser from '@/api/modules/user'
import router from '@/router'

export const useUserStore = defineStore(
  // 唯一ID
  'user',
  () => {
    const settingsStore = useSettingsStore()
    const routeStore = useRouteStore()
    const menuStore = useMenuStore()
    const tabbarStore = useTabbarStore()

    const account = ref(localStorage.account ?? '')
    const token = ref(localStorage.token ?? '')
    const avatar = ref(localStorage.avatar ?? '')
    const user = ref<any>(JSON.parse(localStorage.getItem('user') || 'null'))
    const permissions = ref<string[]>([])
    const isLogin = computed(() => {
      if (token.value) {
        return true
      }
      return false
    })

    // 登录
    async function login(data: {
      account: string
      password: string
    }) {
      const res = await apiUser.login(data)
      const d = res.data
      localStorage.setItem('account', d.user.username)
      localStorage.setItem('token', d.token)
      localStorage.setItem('avatar', '')
      localStorage.setItem('user', JSON.stringify(d.user))
      account.value = d.user.username
      token.value = d.token
      avatar.value = ''
      user.value = d.user
    }

    // 注册
    async function register(data: {
      username: string
      password: string
      invite_code: string
      display_name?: string
    }) {
      const res = await apiUser.register(data)
      const d = res.data
      localStorage.setItem('account', d.user.username)
      localStorage.setItem('token', d.token)
      localStorage.setItem('avatar', '')
      localStorage.setItem('user', JSON.stringify(d.user))
      account.value = d.user.username
      token.value = d.token
      avatar.value = ''
      user.value = d.user
    }

    // 手动登出
    function logout(redirect = router.currentRoute.value.fullPath) {
      // 此处仅清除计算属性 isLogin 中判断登录状态过期的变量，以保证在弹出登录窗口模式下页面展示依旧正常
      localStorage.removeItem('token')
      token.value = ''
      router.push({
        name: 'login',
        query: {
          ...(redirect !== settingsStore.settings.home.fullPath && router.currentRoute.value.name !== 'login' && { redirect }),
        },
      }).then(logoutCleanStatus)
    }
    // 请求登出
    function requestLogout() {
      // 此处仅清除计算属性 isLogin 中判断登录状态过期的变量，以保证在弹出登录窗口模式下页面展示依旧正常
      localStorage.removeItem('token')
      token.value = ''
      router.push({
        name: 'login',
        query: {
          ...(
            router.currentRoute.value.fullPath !== settingsStore.settings.home.fullPath
            && router.currentRoute.value.name !== 'login'
            && {
              redirect: router.currentRoute.value.fullPath,
            }
          ),
        },
      }).then(logoutCleanStatus)
    }
    // 登出后清除状态
    function logoutCleanStatus() {
      localStorage.removeItem('account')
      localStorage.removeItem('avatar')
      localStorage.removeItem('user')
      account.value = ''
      avatar.value = ''
      user.value = null
      permissions.value = []
      settingsStore.updateSettings({}, true)
      tabbarStore.clean()
      routeStore.removeRoutes()
      menuStore.setActived(0)
    }

    // 获取权限
    async function getPermissions() {
      const res = await apiUser.permission()
      permissions.value = res.data.permissions
    }
    // 修改密码
    async function editPassword(data: {
      password: string
      newPassword: string
    }) {
      await apiUser.passwordEdit(data)
    }

    return {
      account,
      token,
      avatar,
      user,
      permissions,
      isLogin,
      login,
      register,
      logout,
      requestLogout,
      getPermissions,
      editPassword,
    }
  },
)

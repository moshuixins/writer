import { hasAllPermissions, hasAnyPermission } from '@/utils/permission'

export default function useAuth() {
  function auth(value: string | string[]) {
    const userStore = useUserStore()
    return hasAnyPermission(userStore.permissions, value)
  }

  function authAll(value: string[]) {
    const userStore = useUserStore()
    return hasAllPermissions(userStore.permissions, value)
  }

  return {
    auth,
    authAll,
  }
}

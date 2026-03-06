import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiAccounts from '@/api/modules/accounts'
import { useUserStore } from '@/store/modules/user'
import type { Account, AccountInvite, AccountUser, RoleInfo, UserRoleSummary } from '@/types/writer'
import { getAdminAccountsPermissionState } from './permissionState'

interface InviteResult {
  code: string
  expires_at: string
}

export function useAdminAccountsPage() {
  const userStore = useUserStore()
  const permissionState = computed(() => getAdminAccountsPermissionState(userStore.permissions, Number(userStore.user?.account_id || 0)))
  const platformAdmin = computed(() => permissionState.value.platformAdmin)
  const canCreateAccount = computed(() => permissionState.value.canCreateAccount)
  const canToggleAccountStatus = computed(() => permissionState.value.canToggleAccountStatus)
  const canEditUserRoles = computed(() => permissionState.value.canEditUserRoles)
  const canRebindUsers = computed(() => permissionState.value.canRebindUsers)
  const canCreateInvite = computed(() => permissionState.value.canCreateInvite)

  const accounts = ref<Account[]>([])
  const users = ref<AccountUser[]>([])
  const invites = ref<AccountInvite[]>([])
  const roles = ref<RoleInfo[]>([])
  const activeTab = ref('users')
  const selectedAccountId = ref<number>(Number(userStore.user?.account_id || 0))

  const loadingAccounts = ref(false)
  const loadingUsers = ref(false)
  const loadingInvites = ref(false)
  const loadingRoles = ref(false)
  const savingUserId = ref(0)

  const createDialogVisible = ref(false)
  const createLoading = ref(false)
  const createForm = reactive({
    code: '',
    name: '',
  })

  const inviteDialogVisible = ref(false)
  const inviteLoading = ref(false)
  const inviteForm = reactive({
    expires_in_hours: 72,
  })
  const inviteResult = ref<InviteResult | null>(null)

  const rebindDialogVisible = ref(false)
  const rebindLoading = ref(false)
  const rebindForm = reactive({
    user_id: 0,
    migrate_data: true,
  })
  const rebindUserName = ref('')

  const currentAccount = computed(() => accounts.value.find(item => item.id === selectedAccountId.value) || null)
  const roleOptions = computed(() => roles.value.filter(item => item.status === 'active').map(item => ({
    code: item.code,
    name: item.name,
    is_system: item.is_system,
  })))

  function mapRoleSummaries(roleCodes: string[]): UserRoleSummary[] {
    return roleCodes.map((code) => {
      const role = roles.value.find(item => item.code === code)
      return role
        ? {
            id: role.id,
            code: role.code,
            name: role.name,
            is_system: role.is_system,
          }
        : null
    }).filter(Boolean) as UserRoleSummary[]
  }

  function syncCurrentUserRoleSnapshot(role: string, roleCodes: string[]) {
    if (!userStore.user) {
      return
    }
    userStore.user.role = role
    userStore.user.roles = [...roleCodes]
    localStorage.setItem('user', JSON.stringify(userStore.user))
  }

  async function loadAccounts() {
    loadingAccounts.value = true
    try {
      const { data } = await apiAccounts.list()
      accounts.value = data.items || []
      if (!selectedAccountId.value && accounts.value.length) {
        selectedAccountId.value = accounts.value[0].id
      }
      if (selectedAccountId.value && !accounts.value.some(item => item.id === selectedAccountId.value) && accounts.value.length) {
        selectedAccountId.value = accounts.value[0].id
      }
    }
    catch {
      accounts.value = []
      ElMessage.error('加载账户失败')
    }
    finally {
      loadingAccounts.value = false
    }
  }

  async function loadUsers() {
    if (!selectedAccountId.value) {
      users.value = []
      return
    }
    loadingUsers.value = true
    try {
      const { data } = await apiAccounts.listUsers(selectedAccountId.value)
      users.value = data.items || []
    }
    catch {
      users.value = []
      ElMessage.error('加载用户失败')
    }
    finally {
      loadingUsers.value = false
    }
  }

  async function loadInvites() {
    if (!selectedAccountId.value) {
      invites.value = []
      return
    }
    loadingInvites.value = true
    try {
      const { data } = await apiAccounts.listInvites(selectedAccountId.value)
      invites.value = data.items || []
    }
    catch {
      invites.value = []
      ElMessage.error('加载邀请码失败')
    }
    finally {
      loadingInvites.value = false
    }
  }

  async function loadRoles() {
    if (!selectedAccountId.value) {
      roles.value = []
      return
    }
    loadingRoles.value = true
    try {
      const { data } = await apiAccounts.roles(selectedAccountId.value)
      roles.value = data.items || []
    }
    catch {
      roles.value = []
      ElMessage.error('加载角色失败')
    }
    finally {
      loadingRoles.value = false
    }
  }

  async function loadAccountDetails() {
    await Promise.all([loadUsers(), loadInvites(), loadRoles()])
  }

  async function reloadAll() {
    await loadAccounts()
    await loadAccountDetails()
  }

  async function onAccountChange(row?: Account) {
    if (!row) {
      return
    }
    selectedAccountId.value = row.id
    await loadAccountDetails()
  }

  async function createAccount() {
    if (!createForm.code.trim() || !createForm.name.trim()) {
      ElMessage.warning('请填写账户编码和名称')
      return
    }
    createLoading.value = true
    try {
      const { data } = await apiAccounts.create({
        code: createForm.code.trim(),
        name: createForm.name.trim(),
      })
      ElMessage.success('账户已创建')
      createDialogVisible.value = false
      createForm.code = ''
      createForm.name = ''
      await loadAccounts()
      selectedAccountId.value = data.id
      await loadAccountDetails()
    }
    finally {
      createLoading.value = false
    }
  }

  async function toggleStatus(account: Account) {
    const nextStatus = account.status === 'active' ? 'disabled' : 'active'
    await ElMessageBox.confirm(`确定将账户状态改为${nextStatus === 'active' ? '启用' : '停用'}吗？`, '修改状态', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await apiAccounts.updateStatus(account.id, nextStatus)
    ElMessage.success('账户状态已更新')
    await loadAccounts()
  }

  async function changeUserRoles(row: AccountUser, nextCodes: string[]) {
    const previousCodes = [...row.role_codes]
    const previousRoles = [...row.roles]
    row.role_codes = [...nextCodes]
    row.roles = mapRoleSummaries(nextCodes)
    savingUserId.value = row.id
    try {
      const { data } = await apiAccounts.updateUserRoles(selectedAccountId.value, row.id, nextCodes)
      row.role = data.role
      row.role_codes = [...data.role_codes]
      row.roles = mapRoleSummaries(data.role_codes)
      if (Number(userStore.user?.id || 0) === row.id) {
        syncCurrentUserRoleSnapshot(data.role, data.role_codes)
        await userStore.getPermissions()
      }
      ElMessage.success('角色绑定已更新')
    }
    catch {
      row.role_codes = previousCodes
      row.roles = previousRoles
    }
    finally {
      savingUserId.value = 0
    }
  }

  function openInviteDialog() {
    inviteForm.expires_in_hours = 72
    inviteResult.value = null
    inviteDialogVisible.value = true
  }

  async function createInvite() {
    if (!selectedAccountId.value) {
      ElMessage.warning('请先选择账户')
      return
    }
    inviteLoading.value = true
    try {
      const { data } = await apiAccounts.createInvite(selectedAccountId.value, inviteForm.expires_in_hours)
      inviteResult.value = {
        code: data.invite_code,
        expires_at: data.expires_at,
      }
      ElMessage.success('邀请码已生成')
      await loadInvites()
    }
    finally {
      inviteLoading.value = false
    }
  }

  async function copyInviteCode() {
    if (!inviteResult.value?.code) {
      return
    }
    await navigator.clipboard.writeText(inviteResult.value.code)
    ElMessage.success('邀请码已复制')
  }

  async function revokeInvite(row: AccountInvite) {
    await ElMessageBox.confirm('确定撤销该邀请码吗？', '撤销邀请码', {
      confirmButtonText: '撤销',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await apiAccounts.revokeInvite(row.id)
    ElMessage.success('邀请码已撤销')
    await loadInvites()
  }

  function openRebindDialog(row: AccountUser) {
    rebindForm.user_id = row.id
    rebindForm.migrate_data = true
    rebindUserName.value = row.display_name || row.username
    rebindDialogVisible.value = true
  }

  async function submitRebind() {
    if (!selectedAccountId.value || !rebindForm.user_id) {
      return
    }
    rebindLoading.value = true
    try {
      await apiAccounts.rebindUser(selectedAccountId.value, rebindForm.user_id, rebindForm.migrate_data)
      ElMessage.success('用户账户迁移完成')
      rebindDialogVisible.value = false
      await reloadAll()
    }
    finally {
      rebindLoading.value = false
    }
  }

  onMounted(async () => {
    await loadAccounts()
    await loadAccountDetails()
  })

  return {
    activeTab,
    accounts,
    canCreateAccount,
    canCreateInvite,
    canEditUserRoles,
    canRebindUsers,
    canToggleAccountStatus,
    copyInviteCode,
    createAccount,
    createDialogVisible,
    createForm,
    createLoading,
    currentAccount,
    invites,
    inviteDialogVisible,
    inviteForm,
    inviteLoading,
    inviteResult,
    loadInvites,
    loadUsers,
    loadingAccounts,
    loadingInvites,
    loadingRoles,
    loadingUsers,
    onAccountChange,
    openInviteDialog,
    openRebindDialog,
    platformAdmin,
    rebindDialogVisible,
    rebindForm,
    rebindLoading,
    rebindUserName,
    reloadAll,
    revokeInvite,
    roleOptions,
    roles,
    savingUserId,
    selectedAccountId,
    submitRebind,
    toggleStatus,
    users,
    changeUserRoles,
    createInvite,
  }
}

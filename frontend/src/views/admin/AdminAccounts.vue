<template>
  <div class="admin-accounts">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">Account Management</h2>
        <p class="page-subtitle">Manage accounts, users, roles, and invite codes</p>
      </div>
      <div class="actions">
        <el-button type="primary" @click="openCreateDialog">Create Account</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="9">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>Accounts</span>
              <el-button link @click="loadAccounts">Refresh</el-button>
            </div>
          </template>
          <el-table
            :data="accounts"
            v-loading="loadingAccounts"
            highlight-current-row
            @current-change="onAccountChange"
            class="panel-table"
          >
            <el-table-column prop="name" label="Name" min-width="140" />
            <el-table-column prop="code" label="Code" min-width="120" />
            <el-table-column label="Status" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Users" width="80" align="right">
              <template #default="{ row }">{{ row.user_count || 0 }}</template>
            </el-table-column>
            <el-table-column label="Actions" width="120">
              <template #default="{ row }">
                <el-button size="small" @click="toggleStatus(row)">
                  {{ row.status === 'active' ? 'Disable' : 'Enable' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>Account Details</span>
              <span class="card-subtitle">{{ currentAccount?.name || '-' }}</span>
            </div>
          </template>

          <el-tabs v-model="activeTab">
            <el-tab-pane label="Users" name="users">
              <div class="section-actions">
                <el-button link :disabled="!currentAccount" @click="loadUsers">Refresh</el-button>
              </div>
              <el-table :data="users" v-loading="loadingUsers" class="panel-table">
                <el-table-column prop="username" label="Username" min-width="140" />
                <el-table-column prop="display_name" label="Display Name" min-width="140" />
                <el-table-column prop="department" label="Department" min-width="140" />
                <el-table-column label="Role" width="160">
                  <template #default="{ row }">
                    <el-select
                      v-model="row.role"
                      size="small"
                      style="width: 130px"
                      :disabled="!roleOptions.length"
                      @change="(value) => changeUserRole(row, String(value))"
                    >
                      <el-option v-for="role in roleOptions" :key="role" :label="role" :value="role" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="Created" width="160">
                  <template #default="{ row }">{{ row.created_at }}</template>
                </el-table-column>
                <el-table-column label="Actions" width="120">
                  <template #default="{ row }">
                    <el-button size="small" @click="openRebindDialog(row)">Move</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane label="Invite Codes" name="invites">
              <div class="section-actions">
                <el-button type="primary" :disabled="!currentAccount" @click="openInviteDialog">Create Invite</el-button>
                <el-button link :disabled="!currentAccount" @click="loadInvites">Refresh</el-button>
              </div>
              <el-table :data="invites" v-loading="loadingInvites" class="panel-table">
                <el-table-column prop="id" label="ID" width="90" />
                <el-table-column prop="status" label="Status" width="110">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_by" label="Created By" width="120" />
                <el-table-column prop="used_by" label="Used By" width="120" />
                <el-table-column prop="created_at" label="Created At" width="160" />
                <el-table-column prop="expires_at" label="Expires At" width="160" />
                <el-table-column label="Actions" width="120">
                  <template #default="{ row }">
                    <el-button size="small" type="danger" @click="revokeInvite(row)" :disabled="row.status !== 'active'">
                      Revoke
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="createDialogVisible" title="Create Account" width="420px" align-center>
      <el-form label-width="120px">
        <el-form-item label="Code">
          <el-input v-model="createForm.code" placeholder="account code" />
        </el-form-item>
        <el-form-item label="Name">
          <el-input v-model="createForm.name" placeholder="account name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="createLoading" @click="createAccount">Create</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="inviteDialogVisible" title="Create Invite" width="420px" align-center>
      <el-form label-width="140px">
        <el-form-item label="Expires (hours)">
          <el-input-number v-model="inviteForm.expires_in_hours" :min="1" :max="720" />
        </el-form-item>
        <el-form-item v-if="inviteResult" label="Invite Code">
          <el-input v-model="inviteResult.code" readonly />
          <el-button class="copy-btn" @click="copyInviteCode">Copy</el-button>
        </el-form-item>
        <el-form-item v-if="inviteResult" label="Expires At">
          <el-input v-model="inviteResult.expires_at" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inviteDialogVisible = false">Close</el-button>
        <el-button type="primary" :loading="inviteLoading" @click="createInvite">Create</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rebindDialogVisible" title="Move User" width="420px" align-center>
      <el-form label-width="120px">
        <el-form-item label="Target Account">
          <el-select v-model="rebindForm.target_account_id" style="width: 220px">
            <el-option
              v-for="acc in targetAccounts"
              :key="acc.id"
              :label="acc.name"
              :value="acc.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Migrate Data">
          <el-switch v-model="rebindForm.migrate_data" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rebindDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="rebindLoading" @click="confirmRebind">Move</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiAccounts from '@/api/modules/accounts'
import type { Account, AccountInvite, AccountUser, RoleInfo } from '@/types/writer'

const accounts = ref<Account[]>([])
const users = ref<AccountUser[]>([])
const invites = ref<AccountInvite[]>([])
const roles = ref<RoleInfo[]>([])

const loadingAccounts = ref(false)
const loadingUsers = ref(false)
const loadingInvites = ref(false)

const selectedAccountId = ref<number | null>(null)
const activeTab = ref('users')

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
const inviteResult = ref<{ code: string; expires_at: string } | null>(null)

const rebindDialogVisible = ref(false)
const rebindLoading = ref(false)
const rebindForm = reactive({
  user_id: 0,
  target_account_id: 0,
  migrate_data: true,
})

const currentAccount = computed(() => accounts.value.find(item => item.id === selectedAccountId.value) || null)
const roleOptions = computed(() => roles.value.map(role => role.role))
const targetAccounts = computed(() =>
  accounts.value.filter(acc => acc.id !== selectedAccountId.value),
)

async function loadAccounts() {
  loadingAccounts.value = true
  try {
    const { data } = await apiAccounts.list()
    accounts.value = data.items || []
    if (!selectedAccountId.value && accounts.value.length) {
      selectedAccountId.value = accounts.value[0].id
    }
    if (selectedAccountId.value) {
      await Promise.all([loadUsers(), loadInvites()])
    }
  } catch {
    accounts.value = []
    users.value = []
    invites.value = []
  } finally {
    loadingAccounts.value = false
  }
}

async function loadRoles() {
  try {
    const { data } = await apiAccounts.roles()
    roles.value = data.items || []
  } catch {
    roles.value = []
  }
}

async function loadUsers() {
  if (!selectedAccountId.value) return
  loadingUsers.value = true
  try {
    const { data } = await apiAccounts.listUsers(selectedAccountId.value)
    users.value = data.items || []
  } catch {
    users.value = []
  } finally {
    loadingUsers.value = false
  }
}

async function loadInvites() {
  if (!selectedAccountId.value) return
  loadingInvites.value = true
  try {
    const { data } = await apiAccounts.listInvites(selectedAccountId.value)
    invites.value = data.items || []
  } catch {
    invites.value = []
  } finally {
    loadingInvites.value = false
  }
}

function onAccountChange(row: Account | undefined) {
  if (!row) return
  selectedAccountId.value = row.id
  loadUsers()
  loadInvites()
}

function openCreateDialog() {
  createForm.code = ''
  createForm.name = ''
  createDialogVisible.value = true
}

async function createAccount() {
  if (!createForm.code || !createForm.name) {
    ElMessage.warning('Please input code and name')
    return
  }
  createLoading.value = true
  try {
    const { data } = await apiAccounts.create({ code: createForm.code.trim(), name: createForm.name.trim() })
    createDialogVisible.value = false
    await loadAccounts()
    selectedAccountId.value = data.id
    ElMessage.success('Account created')
  } catch {
    // handled by interceptor
  } finally {
    createLoading.value = false
  }
}

async function toggleStatus(account: Account) {
  const nextStatus = account.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(`Set account status to ${nextStatus}?`, 'Confirm', {
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await apiAccounts.updateStatus(account.id, nextStatus as 'active' | 'disabled')
    ElMessage.success('Status updated')
    await loadAccounts()
  } catch {
    // handled by interceptor
  }
}

async function changeUserRole(user: AccountUser, role: string) {
  if (!selectedAccountId.value) return
  try {
    await apiAccounts.updateUserRole(selectedAccountId.value, user.id, role)
    ElMessage.success('Role updated')
  } catch {
    await loadUsers()
  }
}

function openInviteDialog() {
  inviteForm.expires_in_hours = 72
  inviteResult.value = null
  inviteDialogVisible.value = true
}

async function createInvite() {
  if (!selectedAccountId.value) return
  inviteLoading.value = true
  try {
    const { data } = await apiAccounts.createInvite(selectedAccountId.value, inviteForm.expires_in_hours)
    inviteResult.value = {
      code: data.invite_code,
      expires_at: data.expires_at,
    }
    await loadInvites()
    ElMessage.success('Invite created')
  } catch {
    // handled by interceptor
  } finally {
    inviteLoading.value = false
  }
}

async function copyInviteCode() {
  if (!inviteResult.value?.code) return
  try {
    await navigator.clipboard.writeText(inviteResult.value.code)
    ElMessage.success('Copied')
  } catch {
    ElMessage.warning('Copy failed')
  }
}

async function revokeInvite(invite: AccountInvite) {
  try {
    await ElMessageBox.confirm('Revoke this invite code?', 'Confirm', { type: 'warning' })
  } catch {
    return
  }
  try {
    await apiAccounts.revokeInvite(invite.id)
    await loadInvites()
    ElMessage.success('Invite revoked')
  } catch {
    // handled by interceptor
  }
}

function openRebindDialog(user: AccountUser) {
  if (!selectedAccountId.value) return
  rebindForm.user_id = user.id
  rebindForm.target_account_id = targetAccounts.value.length ? targetAccounts.value[0].id : 0
  rebindForm.migrate_data = true
  rebindDialogVisible.value = true
}

async function confirmRebind() {
  if (!selectedAccountId.value || !rebindForm.user_id || !rebindForm.target_account_id) {
    ElMessage.warning('Select a target account')
    return
  }
  rebindLoading.value = true
  try {
    await apiAccounts.rebindUser(rebindForm.target_account_id, rebindForm.user_id, rebindForm.migrate_data)
    ElMessage.success('User moved')
    rebindDialogVisible.value = false
    await loadAccounts()
  } catch {
    // handled by interceptor
  } finally {
    rebindLoading.value = false
  }
}

onMounted(() => {
  loadAccounts()
  loadRoles()
})
</script>

<style scoped>
.admin-accounts {
  padding: 24px;
  color: var(--w-color-black);
  background: linear-gradient(180deg, var(--w-color-white) 0%, var(--w-gray-50) 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--w-color-black);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--w-gray-600);
}

.actions {
  display: flex;
  gap: 8px;
}

.panel-card {
  border-radius: var(--w-radius-md);
  border: 1px solid var(--w-gray-200);
  box-shadow: var(--w-shadow-xs);
}

.panel-table {
  border-radius: var(--w-radius-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-subtitle {
  font-size: 12px;
  color: var(--w-gray-500);
}

.section-actions {
  margin-bottom: 10px;
  display: flex;
  gap: 8px;
}

.copy-btn {
  margin-left: 8px;
}

@media (max-width: 992px) {
  .admin-accounts {
    padding: 16px;
  }
}
</style>

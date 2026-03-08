<script setup lang="ts">
import type { AccountUser } from '@/types/writer'
import ActionBar from '@/components/ActionBar/index.vue'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
import MetaTag from '@/components/MetaTag/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import StatusBadge from '@/components/StatusBadge/index.vue'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import { useAdminAccountsPage } from './useAdminAccountsPage'

const {
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
} = useAdminAccountsPage()

function formatDate(value?: string | null) {
  return value ? dayjs(value).tz(SHANGHAI_TZ).format('YYYY-MM-DD HH:mm') : '-'
}

function accountStatusLabel(status: string) {
  return status === 'active' ? '启用' : '停用'
}

function accountStatusTone(status: string): 'neutral' | 'success' {
  return status === 'active' ? 'success' : 'neutral'
}

function inviteStatusLabel(status: string) {
  if (status === 'active') {
    return '待使用'
  }
  if (status === 'used') {
    return '已使用'
  }
  if (status === 'revoked') {
    return '已撤销'
  }
  return status
}

function inviteStatusTone(status: string): 'neutral' | 'success' | 'danger' {
  if (status === 'active') {
    return 'success'
  }
  if (status === 'revoked') {
    return 'danger'
  }
  return 'neutral'
}

const roleEditorVisible = ref(false)
const roleEditorTarget = ref<AccountUser | null>(null)
const roleEditorCodes = ref<string[]>([])

const roleEditorTitle = computed(() => {
  if (!roleEditorTarget.value) {
    return '调整角色'
  }
  const displayName = roleEditorTarget.value.display_name || roleEditorTarget.value.username
  return `调整角色：${displayName}`
})

function visibleRoles(row: AccountUser) {
  return row.roles.slice(0, 1)
}

function remainingRoleCount(row: AccountUser) {
  return Math.max(row.roles.length - 1, 0)
}

function roleSummaryLabel(row: AccountUser) {
  return row.role || '未分配角色'
}

function roleSummaryTitle(row: AccountUser) {
  if (!row.roles.length) {
    return '未分配角色'
  }
  return row.roles.map(role => role.name).join('、')
}

function openRoleEditor(row: AccountUser) {
  roleEditorTarget.value = row
  roleEditorCodes.value = [...row.role_codes]
  roleEditorVisible.value = true
}

function closeRoleEditor() {
  roleEditorVisible.value = false
  roleEditorTarget.value = null
  roleEditorCodes.value = []
}

async function submitRoleEditor() {
  if (!roleEditorTarget.value) {
    return
  }
  const changed = await changeUserRoles(roleEditorTarget.value, [...roleEditorCodes.value])
  if (changed) {
    closeRoleEditor()
  }
}

watch(selectedAccountId, () => {
  closeRoleEditor()
})
</script>

<template>
  <PageShell>
    <PageHeader
      title="账户与用户"
      subtitle="按账户管理启停状态、用户角色绑定、邀请码和账户迁移。"
    >
      <template #actions>
        <el-button :loading="loadingAccounts" @click="reloadAll">
          刷新数据
        </el-button>
        <el-button v-if="canCreateInvite" :disabled="!currentAccount" @click="openInviteDialog">
          生成邀请码
        </el-button>
        <el-button v-if="canCreateAccount" type="primary" @click="createDialogVisible = true">
          新建账户
        </el-button>
      </template>
    </PageHeader>

    <div class="admin-accounts-grid">
      <PanelCard
        title="账户列表"
        :subtitle="platformAdmin ? '平台管理员可查看并维护全部账户' : '当前账户视角仅展示已授权账户'"
      >
        <div v-loading="loadingAccounts" class="account-list">
          <EmptyState
            v-if="!accounts.length"
            title="暂无账户数据"
            description="账户创建后会显示在这里，并可继续绑定用户与邀请码。"
          />
          <button
            v-for="account in accounts"
            :key="account.id"
            type="button"
            class="account-list__item"
            :class="{ 'is-active': account.id === selectedAccountId }"
            @click="onAccountChange(account)"
          >
            <div class="account-list__body">
              <div class="account-list__header">
                <span class="account-list__name">{{ account.name }}</span>
                <StatusBadge :label="accountStatusLabel(account.status)" :tone="accountStatusTone(account.status)" />
              </div>
              <div class="account-list__meta">
                <span>{{ account.code }}</span>
                <span>{{ account.user_count || 0 }} 人</span>
              </div>
            </div>
            <el-button v-if="canToggleAccountStatus" text size="small" @click.stop="toggleStatus(account)">
              {{ account.status === 'active' ? '停用' : '启用' }}
            </el-button>
          </button>
        </div>
      </PanelCard>

      <div class="admin-accounts-main">
        <ActionBar muted>
          <span class="account-meta">当前账户：{{ currentAccount?.name || '未选择账户' }}</span>
          <span class="account-meta">账户编码：{{ currentAccount?.code || '-' }}</span>
          <span class="account-meta">角色数量：{{ roles.length }}</span>
          <span class="account-meta">角色状态：{{ loadingRoles ? '加载中' : '已同步' }}</span>
        </ActionBar>

        <PanelCard
          title="账户详情"
          :subtitle="currentAccount ? '用户、邀请码等数据均按当前账户隔离管理' : '请先在左侧选择一个账户'"
        >
          <el-tabs v-model="activeTab" class="account-tabs">
            <el-tab-pane label="用户" name="users">
              <DataTableShell>
                <el-table v-loading="loadingUsers" :data="users" table-layout="fixed">
                  <template #empty>
                    <EmptyState title="当前账户暂无用户" description="用户注册或绑定到账户后，会在这里显示并分配角色。" />
                  </template>

                  <el-table-column prop="username" label="用户名" min-width="128" show-overflow-tooltip />
                  <el-table-column label="用户信息" min-width="156">
                    <template #default="{ row }">
                      <div class="user-meta" :title="`${row.display_name || '未设置姓名'} / ${row.department || '未设置部门'}`">
                        <div class="user-meta__name">
                          {{ row.display_name || '未设置姓名' }}
                        </div>
                        <div class="user-meta__sub">
                          {{ row.department || '未设置部门' }}
                        </div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="角色摘要" min-width="168">
                    <template #default="{ row }">
                      <div class="role-summary" :title="roleSummaryTitle(row)">
                        <div class="role-tags">
                          <MetaTag
                            v-for="role in visibleRoles(row)"
                            :key="`${row.id}-${role.code}`"
                            :label="role.name"
                            :tone="role.is_system ? 'warning' : 'muted'"
                          />
                          <MetaTag v-if="remainingRoleCount(row) > 0" :label="`+${remainingRoleCount(row)}`" tone="accent" />
                          <MetaTag v-if="!row.roles.length" label="未分配" tone="muted" />
                        </div>
                        <div class="role-summary__primary">
                          主角色：{{ roleSummaryLabel(row) }}
                        </div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="创建时间" width="140">
                    <template #default="{ row }">
                      {{ formatDate(row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column v-if="canEditUserRoles || canRebindUsers" label="操作" width="120">
                    <template #default="{ row }">
                      <div class="role-row-actions">
                        <el-button
                          v-if="canEditUserRoles"
                          text
                          size="small"
                          :disabled="!roleOptions.length"
                          :loading="savingUserId === row.id"
                          @click="openRoleEditor(row)"
                        >
                          调整角色
                        </el-button>
                        <el-button v-if="canRebindUsers" text size="small" @click="openRebindDialog(row)">
                          迁移账户
                        </el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </DataTableShell>
            </el-tab-pane>

            <el-tab-pane label="邀请码" name="invites">
              <DataTableShell>
                <el-table v-loading="loadingInvites" :data="invites">
                  <template #empty>
                    <EmptyState title="当前账户暂无邀请码" description="生成邀请码后，可在这里查看状态、有效期和撤销结果。" />
                  </template>

                  <el-table-column prop="id" label="ID" width="80" />
                  <el-table-column label="状态" width="110">
                    <template #default="{ row }">
                      <StatusBadge :label="inviteStatusLabel(row.status)" :tone="inviteStatusTone(row.status)" />
                    </template>
                  </el-table-column>
                  <el-table-column prop="created_by" label="创建人" width="90" />
                  <el-table-column prop="used_by" label="使用人" width="90" />
                  <el-table-column label="创建时间" width="180">
                    <template #default="{ row }">
                      {{ formatDate(row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="过期时间" width="180">
                    <template #default="{ row }">
                      {{ formatDate(row.expires_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column v-if="canCreateInvite" label="操作" width="120">
                    <template #default="{ row }">
                      <el-button text size="small" :disabled="row.status !== 'active'" @click="revokeInvite(row)">
                        撤销邀请码
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </DataTableShell>
            </el-tab-pane>
          </el-tabs>
        </PanelCard>
      </div>
    </div>

    <el-drawer
      v-model="roleEditorVisible"
      :title="roleEditorTitle"
      size="420px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="savingUserId === 0"
    >
      <div class="role-editor">
        <ActionBar muted class="role-editor__meta">
          <span class="account-meta">当前账户：{{ currentAccount?.name || '-' }}</span>
          <span class="account-meta">目标用户：{{ roleEditorTarget?.display_name || roleEditorTarget?.username || '-' }}</span>
        </ActionBar>

        <div v-if="roleOptions.length" class="role-editor__checks">
          <el-checkbox-group v-model="roleEditorCodes" class="role-editor__group">
            <el-checkbox v-for="role in roleOptions" :key="role.code" :value="role.code" border class="role-editor__option">
              <div class="role-editor__option-body">
                <div class="role-editor__option-title">
                  <span>{{ role.name }}</span>
                  <MetaTag :label="role.is_system ? '系统' : '自定义'" :tone="role.is_system ? 'warning' : 'muted'" />
                </div>
                <div class="role-editor__option-code">
                  {{ role.code }}
                </div>
              </div>
            </el-checkbox>
          </el-checkbox-group>
        </div>
        <EmptyState v-else title="暂无可分配角色" description="请先前往角色与权限页创建或启用角色。" />
      </div>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="closeRoleEditor">
            取消
          </el-button>
          <el-button
            v-if="canEditUserRoles"
            type="primary"
            :loading="savingUserId === Number(roleEditorTarget?.id || 0)"
            :disabled="!roleOptions.length"
            @click="submitRoleEditor"
          >
            保存角色
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="createDialogVisible" title="新建账户" width="420px" align-center>
      <el-form label-position="top">
        <el-form-item label="账户编码">
          <el-input v-model="createForm.code" placeholder="如：bureau-a" />
        </el-form-item>
        <el-form-item label="账户名称">
          <el-input v-model="createForm.name" placeholder="请输入账户名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="createDialogVisible = false">
            取消
          </el-button>
          <el-button v-if="canCreateAccount" type="primary" :loading="createLoading" @click="createAccount">
            创建账户
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="inviteDialogVisible" title="创建邀请码" width="420px" align-center>
      <el-form label-position="top">
        <el-form-item label="有效期（小时）">
          <el-input-number v-model="inviteForm.expires_in_hours" :min="1" :max="720" />
        </el-form-item>
        <el-form-item v-if="inviteResult" label="邀请码">
          <div class="invite-result">
            <el-input :model-value="inviteResult.code" readonly />
            <el-button @click="copyInviteCode">
              复制
            </el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="inviteResult" label="过期时间">
          <el-input :model-value="inviteResult.expires_at" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="inviteDialogVisible = false">
            关闭
          </el-button>
          <el-button v-if="canCreateInvite" type="primary" :loading="inviteLoading" @click="createInvite">
            生成邀请码
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="rebindDialogVisible" title="迁移用户账户" width="460px" align-center>
      <el-form label-position="top">
        <el-form-item label="用户">
          <el-input :model-value="rebindUserName" disabled />
        </el-form-item>
        <el-form-item label="迁移业务数据">
          <el-switch v-model="rebindForm.migrate_data" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="rebindDialogVisible = false">
            取消
          </el-button>
          <el-button v-if="canRebindUsers" type="primary" :loading="rebindLoading" @click="submitRebind">
            确认迁移
          </el-button>
        </div>
      </template>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
.admin-accounts-grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.72fr) minmax(0, 1.88fr);
  gap: 18px;
}

.admin-accounts-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.account-list__item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  width: 100%;
  padding: 14px 14px 12px;
  text-align: left;
  background: rgb(255 255 255 / 72%);
  border: 1px solid var(--w-divider);
  border-radius: 16px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.account-list__item:hover {
  border-color: rgb(17 17 17 / 14%);
  box-shadow: 0 12px 22px rgb(17 17 17 / 5%);
  transform: translateY(-1px);
}

.account-list__item.is-active {
  background: #f7f2e8;
  border-color: rgb(17 17 17 / 16%);
  box-shadow: 0 14px 28px rgb(17 17 17 / 6%);
}

.account-list__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.account-list__header {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.account-list__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 600;
  color: var(--w-text-primary);
  white-space: nowrap;
}

.account-list__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  font-family: var(--w-font-mono);
  font-size: 12px;
  color: var(--w-text-tertiary);
}

.account-meta {
  font-size: 13px;
  color: var(--w-text-secondary);
}

.account-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.user-meta__name,
.user-meta__sub {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-meta__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.user-meta__sub {
  font-size: 12px;
  color: var(--w-text-secondary);
}

.role-tags {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.role-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.role-summary__primary {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: var(--w-text-secondary);
  white-space: nowrap;
}

.role-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.role-editor__meta {
  margin-bottom: 4px;
}

.role-editor__checks {
  max-height: calc(100vh - 240px);
  padding-right: 4px;
  overflow: auto;
}

.role-editor__group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.role-editor__option {
  width: 100%;
  height: auto;
  padding: 12px 14px;
  margin-right: 0;
  background: var(--w-panel-bg);
  border-color: var(--w-panel-border);
  border-radius: 14px;
}

.role-editor__option :deep(.el-checkbox__label) {
  width: 100%;
  padding-left: 12px;
}

.role-editor__option-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.role-editor__option-title {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.role-editor__option-code {
  font-family: var(--w-font-mono);
  font-size: 12px;
  color: var(--w-text-secondary);
}

.invite-result {
  display: flex;
  gap: 8px;
  align-items: center;
}

.invite-result :deep(.el-input) {
  flex: 1;
}

.dialog-actions,
.role-row-actions {
  display: flex;
  flex-flow: column nowrap;
  gap: 4px;
  align-items: flex-start;
}

.dialog-actions {
  flex-flow: row nowrap;
  gap: 8px;
  align-items: center;
}

@media (max-width: 1080px) {
  .admin-accounts-grid {
    grid-template-columns: 1fr;
  }
}
</style>

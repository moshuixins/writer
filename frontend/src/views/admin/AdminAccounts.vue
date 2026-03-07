<script setup lang="ts">
import ActionBar from '@/components/ActionBar/index.vue'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
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
        <DataTableShell>
          <el-table
            v-loading="loadingAccounts"
            :data="accounts"
            :current-row-key="selectedAccountId"
            row-key="id"
            highlight-current-row
            @current-change="onAccountChange"
          >
            <template #empty>
              <EmptyState title="暂无账户数据" description="账户创建后会显示在这里，并可继续绑定用户与邀请码。" />
            </template>

            <el-table-column prop="name" label="账户名称" min-width="150" />
            <el-table-column prop="code" label="编码" min-width="140" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <StatusBadge :label="accountStatusLabel(row.status)" :tone="accountStatusTone(row.status)" />
              </template>
            </el-table-column>
            <el-table-column prop="user_count" label="用户数" width="90" align="right" />
            <el-table-column v-if="canToggleAccountStatus" label="操作" width="110">
              <template #default="{ row }">
                <el-button text size="small" @click.stop="toggleStatus(row)">
                  {{ row.status === 'active' ? '停用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </DataTableShell>
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
                <el-table v-loading="loadingUsers" :data="users">
                  <template #empty>
                    <EmptyState title="当前账户暂无用户" description="用户注册或绑定到账户后，会在这里显示并分配角色。" />
                  </template>

                  <el-table-column prop="username" label="用户名" min-width="140" />
                  <el-table-column prop="display_name" label="姓名" min-width="120" />
                  <el-table-column prop="department" label="部门" min-width="140" />
                  <el-table-column label="角色绑定" min-width="320">
                    <template #default="{ row }">
                      <div class="role-cell">
                        <div class="role-tags">
                          <el-tag
                            v-for="role in row.roles"
                            :key="`${row.id}-${role.code}`"
                            size="small"
                            :type="role.is_system ? 'warning' : 'info'"
                          >
                            {{ role.name }}
                          </el-tag>
                        </div>
                        <el-select
                          v-model="row.role_codes"
                          multiple
                          collapse-tags
                          collapse-tags-tooltip
                          class="role-select"
                          :disabled="!canEditUserRoles || !roleOptions.length || savingUserId === row.id"
                          @change="value => changeUserRoles(row, Array.isArray(value) ? value.map(item => String(item)) : [])"
                        >
                          <el-option
                            v-for="role in roleOptions"
                            :key="role.code"
                            :label="`${role.name} (${role.code})`"
                            :value="role.code"
                          />
                        </el-select>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="创建时间" width="170">
                    <template #default="{ row }">
                      {{ formatDate(row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column v-if="canRebindUsers" label="操作" width="120">
                    <template #default="{ row }">
                      <el-button text size="small" @click="openRebindDialog(row)">
                        迁移账户
                      </el-button>
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
  grid-template-columns: minmax(300px, 0.9fr) minmax(0, 1.5fr);
  gap: 16px;
}

.admin-accounts-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-meta {
  font-size: 13px;
  color: var(--w-text-secondary);
}

.account-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.role-cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.role-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.role-select {
  width: 100%;
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
  gap: 8px;
  align-items: center;
}

@media (max-width: 1080px) {
  .admin-accounts-grid {
    grid-template-columns: 1fr;
  }
}
</style>

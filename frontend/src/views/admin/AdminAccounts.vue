<template>
  <div class="admin-accounts">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">账户与用户管理</h2>
        <p class="page-subtitle">管理账户状态、用户角色、多角色绑定和一次性邀请码。</p>
      </div>
      <div class="header-actions">
        <el-button @click="reloadAll">刷新</el-button>
        <el-button v-if="canCreateAccount" type="primary" @click="createDialogVisible = true">新建账户</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="9">
        <AdminAccountsList
          :accounts="accounts"
          :loading="loadingAccounts"
          :platform-admin="platformAdmin"
          :can-toggle-account-status="canToggleAccountStatus"
          :selected-account-id="selectedAccountId"
          @account-change="onAccountChange"
          @toggle-status="toggleStatus"
        />
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>账户详情</span>
              <span class="card-subtitle">{{ currentAccount?.name || '-' }}</span>
            </div>
          </template>

          <el-tabs v-model="activeTab">
            <AdminAccountUsersTab
              :current-account="currentAccount"
              :users="users"
              :loading="loadingUsers"
              :can-edit-user-roles="canEditUserRoles"
              :can-rebind-users="canRebindUsers"
              :role-options="roleOptions"
              :saving-user-id="savingUserId"
              @refresh="loadUsers"
              @rebind="openRebindDialog"
              @update-roles="changeUserRoles"
            />
            <AdminAccountInvitesTab
              :current-account="currentAccount"
              :invites="invites"
              :loading="loadingInvites"
              :can-create-invite="canCreateInvite"
              @open-invite="openInviteDialog"
              @refresh="loadInvites"
              @revoke="revokeInvite"
            />
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="createDialogVisible" title="新建账户" width="420px" align-center>
      <el-form label-width="100px">
        <el-form-item label="编码">
          <el-input v-model="createForm.code" placeholder="如: bureau-a" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="请输入账户名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button v-if="canCreateAccount" type="primary" :loading="createLoading" @click="createAccount">创建</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="inviteDialogVisible" title="创建邀请码" width="420px" align-center>
      <el-form label-width="120px">
        <el-form-item label="有效期(小时)">
          <el-input-number v-model="inviteForm.expires_in_hours" :min="1" :max="720" />
        </el-form-item>
        <el-form-item v-if="inviteResult" label="邀请码">
          <div class="invite-result">
            <el-input :model-value="inviteResult.code" readonly />
            <el-button @click="copyInviteCode">复制</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="inviteResult" label="过期时间">
          <el-input :model-value="inviteResult.expires_at" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="inviteDialogVisible = false">关闭</el-button>
          <el-button v-if="canCreateInvite" type="primary" :loading="inviteLoading" @click="createInvite">生成</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="rebindDialogVisible" title="迁移用户账户" width="460px" align-center>
      <el-form label-width="100px">
        <el-form-item label="用户">
          <el-input :model-value="rebindUserName" disabled />
        </el-form-item>
        <el-form-item label="迁移业务数据">
          <el-switch v-model="rebindForm.migrate_data" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="rebindDialogVisible = false">取消</el-button>
          <el-button v-if="canRebindUsers" type="primary" :loading="rebindLoading" @click="submitRebind">确认迁移</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import AdminAccountInvitesTab from './components/AdminAccountInvitesTab.vue'
import AdminAccountsList from './components/AdminAccountsList.vue'
import AdminAccountUsersTab from './components/AdminAccountUsersTab.vue'
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
  loadInvites,
  loadUsers,
  loadingAccounts,
  loadingInvites,
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
  savingUserId,
  selectedAccountId,
  submitRebind,
  toggleStatus,
  users,
  changeUserRoles,
  createInvite,
} = useAdminAccountsPage()
</script>

<style scoped src="./adminAccounts.css"></style>

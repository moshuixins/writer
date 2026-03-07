<script setup lang="ts">
import type { Account, PermissionInfo, RoleInfo } from '@/types/writer'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import apiAccounts from '@/api/modules/accounts'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import StatusBadge from '@/components/StatusBadge/index.vue'
import { getAdminRolesPermissionState } from './permissionState'

const userStore = useUserStore()
const permissionState = computed(() => getAdminRolesPermissionState(userStore.permissions))
const canWriteRoles = computed(() => permissionState.value.canWriteRoles)
const accounts = ref<Account[]>([])
const permissions = ref<PermissionInfo[]>([])
const roles = ref<RoleInfo[]>([])
const loadingRoles = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const selectedAccountId = ref<number>(Number(userStore.user?.account_id || 0))
const roleForm = reactive({
  id: 0,
  code: '',
  name: '',
  description: '',
  status: 'active',
  permission_codes: [] as string[],
})

const isEditing = computed(() => roleForm.id > 0)
const currentAccountName = computed(() => accounts.value.find(item => item.id === selectedAccountId.value)?.name || '-')

function statusLabel(status: string) {
  return status === 'active' ? '启用' : '停用'
}

function statusTone(status: string): 'neutral' | 'success' {
  return status === 'active' ? 'success' : 'neutral'
}

function resetRoleForm() {
  roleForm.id = 0
  roleForm.code = ''
  roleForm.name = ''
  roleForm.description = ''
  roleForm.status = 'active'
  roleForm.permission_codes = []
}

function permissionLabel(code: string) {
  return permissions.value.find(item => item.code === code)?.name || code
}
async function loadAccounts() {
  const { data } = await apiAccounts.list()
  accounts.value = data.items || []
  if (!selectedAccountId.value && accounts.value.length) {
    selectedAccountId.value = accounts.value[0].id
  }
  if (selectedAccountId.value && !accounts.value.some(item => item.id === selectedAccountId.value) && accounts.value.length) {
    selectedAccountId.value = accounts.value[0].id
  }
}

async function loadPermissions() {
  const { data } = await apiAccounts.permissions()
  permissions.value = data.items || []
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

function openCreateDialog() {
  resetRoleForm()
  dialogVisible.value = true
}

function openEditDialog(role: RoleInfo) {
  roleForm.id = role.id
  roleForm.code = role.code
  roleForm.name = role.name
  roleForm.description = role.description
  roleForm.status = role.status
  roleForm.permission_codes = [...role.permissions]
  dialogVisible.value = true
}

async function submitRole() {
  if (!selectedAccountId.value) {
    ElMessage.warning('请先选择账户')
    return
  }
  if (!roleForm.code.trim() || !roleForm.name.trim()) {
    ElMessage.warning('请填写角色编码和名称')
    return
  }
  submitting.value = true
  try {
    const payload = {
      code: roleForm.code.trim(),
      name: roleForm.name.trim(),
      description: roleForm.description.trim(),
      status: roleForm.status,
      permission_codes: [...roleForm.permission_codes],
    }
    if (isEditing.value) {
      await apiAccounts.updateRole(selectedAccountId.value, roleForm.id, {
        name: payload.name,
        description: payload.description,
        status: payload.status,
        permission_codes: payload.permission_codes,
      })
      ElMessage.success('角色已更新')
    }
    else {
      await apiAccounts.createRole(selectedAccountId.value, payload)
      ElMessage.success('角色已创建')
    }
    dialogVisible.value = false
    await loadRoles()
  }
  finally {
    submitting.value = false
  }
}

async function removeRole(role: RoleInfo) {
  await ElMessageBox.confirm(`确定删除角色“${role.name}”吗？`, '删除角色', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await apiAccounts.deleteRole(selectedAccountId.value, role.id)
  ElMessage.success('角色已删除')
  await loadRoles()
}

onMounted(async () => {
  try {
    await Promise.all([loadAccounts(), loadPermissions()])
    await loadRoles()
  }
  catch {
    ElMessage.error('初始化角色页面失败')
  }
})
</script>

<template>
  <PageShell>
    <PageHeader
      title="角色与权限"
      subtitle="按账户维护角色、权限字典和角色可用状态。"
    >
      <template #actions>
        <el-select
          v-model="selectedAccountId"
          class="account-select"
          placeholder="选择账户"
          @change="loadRoles"
        >
          <el-option v-for="account in accounts" :key="account.id" :label="account.name" :value="account.id" />
        </el-select>
        <el-button
          v-if="canWriteRoles"
          type="primary"
          :disabled="!selectedAccountId"
          @click="openCreateDialog"
        >
          新建角色
        </el-button>
      </template>
    </PageHeader>

    <PanelCard
      title="角色列表"
      :subtitle="selectedAccountId ? `当前账户：${currentAccountName}` : '请先选择账户后再维护角色'"
    >
      <DataTableShell>
        <el-table v-loading="loadingRoles" :data="roles">
          <template #empty>
            <EmptyState
              icon="i-ep:key"
              title="当前账户暂无角色"
              description="系统角色和自定义角色都会展示在这里，可按账户单独维护。"
            />
          </template>

          <el-table-column prop="code" label="编码" min-width="140" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <StatusBadge :label="statusLabel(row.status)" :tone="statusTone(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="110">
            <template #default="{ row }">
              <StatusBadge :label="row.is_system ? '系统' : '自定义'" :tone="row.is_system ? 'warning' : 'neutral'" />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
          <el-table-column label="权限" min-width="280">
            <template #default="{ row }">
              <div class="perm-tags">
                <el-tag v-for="perm in row.permissions" :key="`${row.id}-${perm}`" size="small">
                  {{ permissionLabel(perm) }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button v-if="canWriteRoles" text size="small" :disabled="row.is_system" @click="openEditDialog(row)">
                  编辑
                </el-button>
                <el-button v-if="canWriteRoles" text size="small" :disabled="row.is_system" @click="removeRole(row)">
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </DataTableShell>
    </PanelCard>

    <PanelCard title="权限字典" subtitle="展示后端开放的权限编码及其中文说明。">
      <div class="permission-grid">
        <div v-for="perm in permissions" :key="perm.code" class="permission-item">
          <div class="permission-item__name">
            {{ perm.name }}
          </div>
          <div class="permission-item__code">
            {{ perm.code }}
          </div>
          <div class="permission-item__desc">
            {{ perm.description }}
          </div>
        </div>
      </div>
    </PanelCard>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑角色' : '新建角色'" width="720px" align-center>
      <el-form label-position="top">
        <el-form-item label="所属账户">
          <el-input :model-value="currentAccountName" disabled />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="角色编码">
            <el-input v-model="roleForm.code" :disabled="isEditing" placeholder="如：reviewer" />
          </el-form-item>
          <el-form-item label="角色名称">
            <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
          </el-form-item>
        </div>
        <div class="form-grid form-grid--narrow">
          <el-form-item label="状态">
            <el-select v-model="roleForm.status" class="status-select" :disabled="!isEditing">
              <el-option label="启用" value="active" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="角色说明">
          <el-input v-model="roleForm.description" type="textarea" :rows="3" placeholder="请输入角色说明" />
        </el-form-item>
        <el-form-item label="权限分配">
          <el-checkbox-group v-model="roleForm.permission_codes" class="permission-checks">
            <el-checkbox v-for="perm in permissions" :key="perm.code" :label="perm.code">
              <div class="check-label">
                <span>{{ perm.name }}</span>
                <small>{{ perm.code }}</small>
              </div>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <el-button @click="dialogVisible = false">
            取消
          </el-button>
          <el-button v-if="canWriteRoles" type="primary" :loading="submitting" @click="submitRole">
            保存角色
          </el-button>
        </div>
      </template>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
.account-select {
  width: 240px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-grid--narrow {
  grid-template-columns: minmax(0, 200px);
}

.status-select {
  width: 100%;
}

.perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.row-actions,
.dialog-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.permission-item {
  padding: 14px;
  background: var(--w-gray-50);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-md);
}

.permission-item__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.permission-item__code {
  margin-top: 6px;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  color: var(--w-text-tertiary);
}

.permission-item__desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--w-text-secondary);
}

.permission-checks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.check-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.check-label small {
  color: var(--w-text-tertiary);
}

@media (max-width: 900px) {
  .account-select {
    width: 100%;
  }

  .form-grid,
  .permission-checks {
    grid-template-columns: 1fr;
  }
}
</style>

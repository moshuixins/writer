<template>
  <div class="admin-roles">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">角色与权限</h2>
        <p class="page-subtitle">角色、权限与账户绑定均来自数据库，可直接在此管理。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="selectedAccountId" class="account-select" placeholder="选择账户" @change="loadRoles">
          <el-option v-for="item in accounts" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button @click="loadRoles">刷新</el-button>
        <el-button v-if="canWriteRoles" type="primary" :disabled="!selectedAccountId" @click="openCreateDialog">新建角色</el-button>
      </div>
    </div>

    <el-card shadow="never" class="panel-card">
      <template #header>
        <div class="card-header">
          <span>角色列表</span>
          <span class="card-subtitle">{{ currentAccountName }}</span>
        </div>
      </template>

      <el-table :data="roles" v-loading="loadingRoles" class="panel-table">
        <el-table-column prop="code" label="编码" min-width="140" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'warning' : 'info'">
              {{ row.is_system ? '系统' : '自定义' }}
            </el-tag>
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
              <el-button v-if="canWriteRoles" size="small" :disabled="row.is_system" @click="openEditDialog(row)">编辑</el-button>
              <el-button v-if="canWriteRoles" size="small" type="danger" :disabled="row.is_system" @click="removeRole(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>
        <div class="card-header">
          <span>权限字典</span>
        </div>
      </template>
      <div class="permission-grid">
        <div v-for="perm in permissions" :key="perm.code" class="permission-item">
          <div class="permission-name">{{ perm.name }}</div>
          <div class="permission-code">{{ perm.code }}</div>
          <div class="permission-desc">{{ perm.description }}</div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑角色' : '新建角色'" width="720px" align-center>
      <el-form label-width="100px">
        <el-form-item label="账户">
          <el-input :model-value="currentAccountName" disabled />
        </el-form-item>
        <el-form-item label="编码">
          <el-input v-model="roleForm.code" :disabled="isEditing" placeholder="如: reviewer" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="roleForm.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="roleForm.status" style="width: 180px" :disabled="!isEditing">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="roleForm.description" type="textarea" :rows="3" placeholder="请输入角色说明" />
        </el-form-item>
        <el-form-item label="权限">
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
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button v-if="canWriteRoles" type="primary" :loading="submitting" @click="submitRole">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiAccounts from '@/api/modules/accounts'
import type { Account, PermissionInfo, RoleInfo } from '@/types/writer'
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

<style scoped>
.admin-roles {
  padding: 24px;
  color: var(--w-color-black);
  background: linear-gradient(180deg, var(--w-color-white) 0%, var(--w-gray-50) 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header,
.card-header,
.header-actions,
.row-actions,
.dialog-actions {
  display: flex;
  align-items: center;
}

.page-header,
.card-header {
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

.page-subtitle,
.card-subtitle,
.permission-code,
.permission-desc {
  color: var(--w-gray-600);
}

.page-subtitle,
.card-subtitle,
.permission-desc {
  font-size: 13px;
}

.header-actions,
.row-actions,
.dialog-actions {
  gap: 8px;
}

.account-select {
  width: 220px;
}

.panel-card {
  border-radius: var(--w-radius-md);
  border: 1px solid var(--w-gray-200);
  box-shadow: var(--w-shadow-xs);
}

.panel-table {
  border-radius: var(--w-radius-md);
}

.perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.permission-item {
  border: 1px solid var(--w-gray-200);
  border-radius: var(--w-radius-md);
  background: var(--w-color-white);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.permission-name {
  font-size: 14px;
  font-weight: 600;
}

.permission-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
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
  color: var(--w-gray-500);
}

@media (max-width: 768px) {
  .admin-roles {
    padding: 16px;
  }

  .page-header,
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .account-select,
  .permission-checks {
    width: 100%;
    grid-template-columns: 1fr;
  }
}
</style>

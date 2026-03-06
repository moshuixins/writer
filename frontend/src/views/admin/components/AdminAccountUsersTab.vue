<template>
  <el-tab-pane label="用户" name="users">
    <div class="section-actions">
      <el-button link :disabled="!currentAccount" @click="emit('refresh')">刷新用户</el-button>
    </div>
    <el-table :data="users" v-loading="loading" class="panel-table">
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column prop="display_name" label="姓名" min-width="120" />
      <el-table-column prop="department" label="部门" min-width="140" />
      <el-table-column label="角色绑定" min-width="320">
        <template #default="{ row }">
          <div class="role-cell">
            <div class="role-tags">
              <el-tag v-for="role in row.roles" :key="`${row.id}-${role.code}`" size="small" :type="role.is_system ? 'warning' : 'info'">
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
              @change="value => handleRoleChange(row, value)"
            >
              <el-option v-for="role in roleOptions" :key="role.code" :label="`${role.name} (${role.code})`" :value="role.code" />
            </el-select>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="168" />
      <el-table-column v-if="canRebindUsers" label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="emit('rebind', row)">迁移</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-tab-pane>
</template>

<script setup lang="ts">
import type { Account, AccountUser } from '@/types/writer'

interface RoleOption {
  code: string
  name: string
  is_system: boolean
}

defineProps<{
  currentAccount: Account | null
  users: AccountUser[]
  loading: boolean
  canEditUserRoles: boolean
  canRebindUsers: boolean
  roleOptions: RoleOption[]
  savingUserId: number
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'rebind', user: AccountUser): void
  (e: 'update-roles', user: AccountUser, roleCodes: string[]): void
}>()

function handleRoleChange(row: AccountUser, value: unknown) {
  const nextCodes = Array.isArray(value) ? value.map(item => String(item)) : []
  emit('update-roles', row, nextCodes)
}
</script>

<style scoped src="../adminAccounts.css"></style>

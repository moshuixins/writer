<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <div class="card-header">
        <span>账户列表</span>
        <span class="card-subtitle">{{ platformAdmin ? '平台管理员视角' : '当前账户视角' }}</span>
      </div>
    </template>
    <el-table
      :data="accounts"
      :current-row-key="selectedAccountId"
      v-loading="loading"
      row-key="id"
      class="panel-table"
      highlight-current-row
      @current-change="handleCurrentChange"
    >
      <el-table-column prop="name" label="账户名称" min-width="140" />
      <el-table-column prop="code" label="编码" min-width="120" />
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_count" label="用户数" width="88" />
      <el-table-column v-if="canToggleAccountStatus" label="操作" width="116">
        <template #default="{ row }">
          <el-button size="small" @click.stop="emit('toggle-status', row)">
            {{ row.status === 'active' ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { Account } from '@/types/writer'

defineProps<{
  accounts: Account[]
  loading: boolean
  platformAdmin: boolean
  canToggleAccountStatus: boolean
  selectedAccountId: number
}>()

const emit = defineEmits<{
  (e: 'account-change', account?: Account): void
  (e: 'toggle-status', account: Account): void
}>()

function handleCurrentChange(account?: Account) {
  emit('account-change', account)
}
</script>

<style scoped src="../adminAccounts.css"></style>

<template>
  <el-tab-pane label="邀请码" name="invites">
    <div class="section-actions">
      <el-button v-if="canCreateInvite" type="primary" :disabled="!currentAccount" @click="emit('open-invite')">创建邀请码</el-button>
      <el-button link :disabled="!currentAccount" @click="emit('refresh')">刷新邀请码</el-button>
    </div>
    <el-table :data="invites" v-loading="loading" class="panel-table">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="创建人" width="90" />
      <el-table-column prop="used_by" label="使用人" width="90" />
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column prop="expires_at" label="过期时间" width="160" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="canCreateInvite" size="small" type="danger" :disabled="row.status !== 'active'" @click="emit('revoke', row)">
            撤销
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-tab-pane>
</template>

<script setup lang="ts">
import type { Account, AccountInvite } from '@/types/writer'

defineProps<{
  currentAccount: Account | null
  invites: AccountInvite[]
  loading: boolean
  canCreateInvite: boolean
}>()

const emit = defineEmits<{
  (e: 'open-invite'): void
  (e: 'refresh'): void
  (e: 'revoke', invite: AccountInvite): void
}>()
</script>

<style scoped src="../adminAccounts.css"></style>

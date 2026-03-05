<template>
  <div class="admin-overview">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">Admin Overview</h2>
        <p class="page-subtitle">Account, role, and permission administration</p>
      </div>
    </div>

    <div class="summary-grid">
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">Total Accounts</div>
        <div class="summary-value">{{ totalAccounts }}</div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">Active Accounts</div>
        <div class="summary-value">{{ activeAccounts }}</div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">Total Users</div>
        <div class="summary-value">{{ totalUsers }}</div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">Current Account</div>
        <div class="summary-value">{{ myAccount?.name || '-' }}</div>
        <div class="summary-meta">{{ myAccount?.code || '' }}</div>
      </el-card>
    </div>

    <el-card shadow="never" class="quick-card">
      <template #header>
        <div class="card-header">
          <span>Quick Actions</span>
        </div>
      </template>
      <div class="quick-actions">
        <el-button type="primary" @click="go('/admin/accounts')">Manage Accounts</el-button>
        <el-button @click="go('/admin/roles')">Roles & Permissions</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import apiAccounts from '@/api/modules/accounts'
import type { Account } from '@/types/writer'

const router = useRouter()
const totalAccounts = ref(0)
const activeAccounts = ref(0)
const totalUsers = ref(0)
const myAccount = ref<Account | null>(null)

function go(path: string) {
  router.push(path)
}

async function loadSummary() {
  try {
    const [accountsRes, meRes] = await Promise.all([
      apiAccounts.list(),
      apiAccounts.me(),
    ])
    const items = accountsRes.data.items || []
    totalAccounts.value = items.length
    activeAccounts.value = items.filter(item => item.status === 'active').length
    totalUsers.value = items.reduce((acc, item) => acc + Number(item.user_count || 0), 0)
    myAccount.value = meRes.data
  } catch {
    ElMessage.error('Failed to load admin overview')
  }
}

onMounted(() => {
  loadSummary()
})
</script>

<style scoped>
.admin-overview {
  padding: 24px;
  color: var(--w-color-black);
  background: linear-gradient(180deg, var(--w-color-white) 0%, var(--w-gray-50) 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.summary-card {
  border-radius: var(--w-radius-md);
  border: 1px solid var(--w-gray-200);
  box-shadow: var(--w-shadow-xs);
}

.summary-label {
  font-size: 12px;
  color: var(--w-gray-600);
}

.summary-value {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 700;
  color: var(--w-color-black);
}

.summary-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--w-gray-500);
}

.quick-card {
  border-radius: var(--w-radius-md);
  border: 1px solid var(--w-gray-200);
  box-shadow: var(--w-shadow-xs);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .admin-overview {
    padding: 16px;
  }
}
</style>

<template>
  <div class="admin-roles">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">Roles & Permissions</h2>
        <p class="page-subtitle">System roles are defined on the server</p>
      </div>
    </div>

    <el-card shadow="never" class="panel-card">
      <template #header>
        <div class="card-header">
          <span>Role Definitions</span>
          <el-button link @click="loadRoles">Refresh</el-button>
        </div>
      </template>
      <el-table :data="roles" v-loading="loading" class="panel-table">
        <el-table-column prop="role" label="Role" width="160" />
        <el-table-column label="Permissions">
          <template #default="{ row }">
            <div class="perm-tags">
              <el-tag
                v-for="perm in row.permissions"
                :key="`${row.role}-${perm}`"
                size="small"
                :type="perm === '*' ? 'danger' : 'info'"
              >
                {{ perm === '*' ? 'ALL' : perm }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>
        <div class="card-header">
          <span>Notes</span>
        </div>
      </template>
      <div class="notes">
        <p>Roles are currently managed by the backend role map.</p>
        <p>To extend permissions, adjust the server-side role configuration.</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import apiAccounts from '@/api/modules/accounts'
import type { RoleInfo } from '@/types/writer'

const roles = ref<RoleInfo[]>([])
const loading = ref(false)

async function loadRoles() {
  loading.value = true
  try {
    const { data } = await apiAccounts.roles()
    roles.value = data.items || []
  } catch {
    roles.value = []
    ElMessage.error('Failed to load roles')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRoles()
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

.perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.notes {
  color: var(--w-gray-600);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .admin-roles {
    padding: 16px;
  }
}
</style>

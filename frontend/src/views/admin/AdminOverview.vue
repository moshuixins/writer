<script setup lang="ts">
import type { Account } from '@/types/writer'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import apiAccounts from '@/api/modules/accounts'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'

const router = useRouter()
const totalAccounts = ref(0)
const activeAccounts = ref(0)
const totalUsers = ref(0)
const myAccount = ref<Account | null>(null)

function go(path: string) {
  void router.push(path)
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
  }
  catch {
    ElMessage.error('加载管理概览失败')
  }
}

onMounted(() => {
  void loadSummary()
})
</script>

<template>
  <PageShell>
    <PageHeader
      title="管理概览"
      subtitle="查看当前账户体系、用户数量与后台管理入口。"
    />

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-card__label">
          账户总数
        </div>
        <div class="metric-card__value">
          {{ totalAccounts }}
        </div>
        <div class="metric-card__meta">
          系统已创建的账户数量
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-card__label">
          启用账户
        </div>
        <div class="metric-card__value">
          {{ activeAccounts }}
        </div>
        <div class="metric-card__meta">
          当前可正常使用的账户数量
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-card__label">
          用户总数
        </div>
        <div class="metric-card__value">
          {{ totalUsers }}
        </div>
        <div class="metric-card__meta">
          按账户统计的用户总量
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-card__label">
          当前账户
        </div>
        <div class="metric-card__value metric-card__value--text">
          {{ myAccount?.name || '-' }}
        </div>
        <div class="metric-card__meta">
          {{ myAccount?.code || '未绑定账户编码' }}
        </div>
      </div>
    </div>

    <div class="overview-grid">
      <PanelCard title="快速操作" subtitle="常用管理操作入口统一放在这里。">
        <div class="overview-actions">
          <el-button type="primary" @click="go('/admin/accounts')">
            进入账户与用户
          </el-button>
          <el-button @click="go('/admin/roles')">
            进入角色与权限
          </el-button>
        </div>
      </PanelCard>

      <PanelCard title="管理提醒" subtitle="保持多账户边界清晰，避免权限过度分配。">
        <ul class="overview-notes">
          <li>账户状态变更会影响其下全部用户与资源访问。</li>
          <li>角色与权限建议按岗位职责最小化配置，不做泛授权。</li>
          <li>邀请码适合短期发放，创建后请及时在账户页核验使用状态。</li>
        </ul>
      </PanelCard>
    </div>
  </PageShell>
</template>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.overview-notes {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 18px;
  margin: 0;
  line-height: 1.7;
  color: var(--w-text-secondary);
}

.metric-card__value--text {
  font-size: 18px;
}

@media (max-width: 900px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>

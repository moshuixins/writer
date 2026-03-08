<script setup lang="ts">
import type { ExportDoc } from '@/types/writer'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import apiDocuments from '@/api/modules/documents'
import ActionBar from '@/components/ActionBar/index.vue'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
import MetaTag from '@/components/MetaTag/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'

const docs = ref<ExportDoc[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function loadHistory() {
  loading.value = true
  try {
    const { data } = await apiDocuments.history({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    docs.value = data.items
    total.value = data.total
  }
  catch {
    docs.value = []
    total.value = 0
  }
  finally {
    loading.value = false
  }
}

async function download(row: ExportDoc) {
  try {
    const resp = await apiDocuments.download(row.id)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.title || '文稿'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  }
  catch {
    ElMessage.error('下载失败，文件可能已失效')
  }
}

function formatDate(value: string) {
  return value ? dayjs(value).tz(SHANGHAI_TZ).format('YYYY-MM-DD HH:mm') : '-'
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  void loadHistory()
}

onMounted(() => {
  void loadHistory()
})
</script>

<template>
  <PageShell>
    <PageHeader
      title="导出历史"
      subtitle="查看已导出的文稿版本，并支持重新下载 docx 文件。"
    >
      <template #actions>
        <el-button :loading="loading" @click="loadHistory">
          刷新记录
        </el-button>
      </template>
    </PageHeader>

    <ActionBar muted>
      <span class="history-summary__item">共 {{ total }} 份导出文稿</span>
      <span class="history-summary__item">当前每页 {{ pageSize }} 条</span>
    </ActionBar>

    <PanelCard
      title="导出记录"
      subtitle="导出成功的文稿会保存在历史列表中，可按版本重新下载。"
    >
      <DataTableShell>
        <el-table v-loading="loading" :data="docs">
          <template #empty>
            <EmptyState
              icon="i-ep:folder-opened"
              title="暂无导出记录"
              description="在写作工作台导出 docx 后，这里会展示对应历史。"
            />
          </template>

          <el-table-column prop="title" label="标题" min-width="260" show-overflow-tooltip />
          <el-table-column prop="doc_type" label="文种" width="140">
            <template #default="{ row }">
              <MetaTag :label="row.doc_type || '其他'" tone="accent" />
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="90" align="center" />
          <el-table-column label="导出时间" width="190">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button text size="small" @click="download(row)">
                下载文稿
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </DataTableShell>

      <div v-if="total > pageSize" class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="loadHistory"
          @size-change="onPageSizeChange"
        />
      </div>
    </PanelCard>
  </PageShell>
</template>

<style scoped>
.history-summary__item {
  font-size: 13px;
  color: var(--w-text-secondary);
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

<template>
  <div class="history-page">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">导出历史</h2>
        <p class="page-subtitle">查看已导出的文档版本并支持重新下载</p>
      </div>
    </div>

    <el-table :data="docs" v-loading="loading" class="history-table">
      <template #empty>
        <div class="empty-state">
          <el-icon :size="40" color="#c0c4cc"><FolderOpened /></el-icon>
          <p>暂无导出记录</p>
        </div>
      </template>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="doc_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.doc_type || '公文' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="80" align="center" />
      <el-table-column label="导出时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination" v-if="total > pageSize">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import apiDocuments from '@/api/modules/documents'
import dayjs from '@/utils/dayjs'
import type { ExportDoc } from '@/types/writer'

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
  } catch {
    docs.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function download(row: ExportDoc) {
  try {
    const resp = await apiDocuments.download(row.id)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.title || '公文'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败，文件可能已被清理')
  }
}

function formatDate(value: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadHistory()
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-title-wrap { display: flex; flex-direction: column; gap: 6px; }
.page-title { margin: 0; font-size: 22px; font-weight: 700; color: var(--el-text-color-primary); }
.page-subtitle { margin: 0; font-size: 13px; color: var(--el-text-color-secondary); }
.history-table { border-radius: 8px; overflow: hidden; }
.empty-state { padding: 40px; text-align: center; color: var(--el-text-color-secondary); }
.empty-state p { margin: 12px 0 0; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }

@media (max-width: 768px) {
  .history-page { padding: 16px; }
}
</style>

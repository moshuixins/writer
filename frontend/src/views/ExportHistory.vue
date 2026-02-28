<template>
  <div class="history-page">
    <h2>导出历史</h2>
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
      <el-table-column prop="created_at" label="导出时间" width="180" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import api from '../api'
import type { ExportDoc } from '../types'

const docs = ref<ExportDoc[]>([])
const loading = ref(false)

async function loadHistory() {
  loading.value = true
  try {
    const { data } = await api.get('/documents/history')
    docs.value = data
  } catch {
    docs.value = []
  } finally {
    loading.value = false
  }
}

async function download(row: any) {
  try {
    const resp = await api.get(`/documents/history/${row.id}/download`, {
      responseType: 'blob',
    })
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

onMounted(loadHistory)
</script>

<style scoped>
.history-page { padding: 24px; }
.history-page h2 { margin: 0 0 16px; font-size: 20px; color: #303133; }
.history-table { border-radius: 8px; overflow: hidden; }
.empty-state { padding: 40px; text-align: center; color: #909399; }
.empty-state p { margin: 12px 0 0; }
</style>

<template>
  <div class="material-manager">
    <div class="header">
      <div class="page-title-wrap">
        <h2 class="page-title">素材管理</h2>
        <p class="page-subtitle">上传并管理历史公文素材，用于检索增强与写作参考</p>
      </div>
      <el-upload
        :action="uploadUrl"
        :headers="uploadHeaders"
        :on-success="onUploadSuccess"
        :on-error="onUploadError"
        :on-progress="onUploadProgress"
        :before-upload="beforeUpload"
        :show-file-list="false"
        accept=".docx,.pdf,.txt"
      >
        <el-button type="primary" :loading="uploading">
          {{ uploading ? '上传中...' : '上传素材' }}
        </el-button>
      </el-upload>
    </div>

    <div class="filters">
      <el-select v-model="filters.docType" placeholder="公文类型" clearable @change="resetAndLoad">
        <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="关键词搜索"
        clearable
        @input="onSearchInput"
        @clear="resetAndLoad"
        class="keyword-input"
      />
    </div>

    <div class="batch-actions" v-if="selectedIds.length > 0">
      <span>已选 {{ selectedIds.length }} 项</span>
      <el-button size="small" type="danger" @click="batchDelete">批量删除</el-button>
      <el-select v-model="batchDocType" placeholder="批量分类" size="small" style="width:120px;margin-left:8px">
        <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button size="small" @click="batchClassify" :disabled="!batchDocType">应用分类</el-button>
    </div>

    <el-table :data="materials" v-loading="loading" class="material-table"
      @selection-change="onSelectionChange">
      <template #empty>
        <div class="empty-state">
          <el-icon :size="40" color="#c0c4cc"><Document /></el-icon>
          <p>暂无素材，点击右上角上传</p>
        </div>
      </template>
      <el-table-column type="selection" width="45" />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="doc_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.doc_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="char_count" label="字数" width="80" align="right" />
      <el-table-column label="上传时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          <el-button link type="danger" size="small" @click="deleteMaterial(row.id)">删除</el-button>
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
        @current-change="loadMaterials"
        @size-change="onPageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import apiMaterials from '@/api/modules/materials'
import { DOC_TYPES } from '@/utils/constants'
import dayjs from '@/utils/dayjs'
import type { Material, MaterialListParams } from '@/types/writer'
import { useUserStore } from '@/store/modules/user'

const userStore = useUserStore()

const materials = ref<Material[]>([])
const loading = ref(false)
const uploading = ref(false)
const selectedIds = ref<number[]>([])
const batchDocType = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const uploadUrl = apiMaterials.uploadUrl
const uploadHeaders = computed(() => {
  return userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}
})

const filters = reactive({
  docType: '',
  keyword: '',
})

async function loadMaterials() {
  loading.value = true
  try {
    const params: MaterialListParams = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    if (filters.docType) params.doc_type = filters.docType
    if (filters.keyword) params.keyword = filters.keyword
    const { data } = await apiMaterials.list(params)
    materials.value = data.items
    total.value = data.total
    selectedIds.value = []
  } catch {
    materials.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  currentPage.value = 1
  loadMaterials()
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(resetAndLoad, 400)
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadMaterials()
}

const MAX_FILE_SIZE = 50 * 1024 * 1024

function beforeUpload(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['docx', 'pdf', 'txt'].includes(ext || '')) {
    ElMessage.error('仅支持 .docx .pdf .txt 格式')
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

function onUploadProgress() { uploading.value = true }

function onUploadSuccess() {
  uploading.value = false
  ElMessage.success('上传成功，正在分析...')
  resetAndLoad()
}

function onUploadError() {
  uploading.value = false
  ElMessage.error('上传失败')
}

function showDetail(row: Material) {
  const keywords = (row.keywords || []).join('、')
  ElMessageBox.alert(
    `类型：${row.doc_type}\n摘要：${row.summary || '无'}\n关键词：${keywords}`,
    row.title,
  )
}

async function deleteMaterial(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该素材？删除后不可恢复', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }

  try {
    await apiMaterials.delete(id)
    ElMessage.success('已删除')
    loadMaterials()
  } catch {
    // interceptor handles
  }
}

function onSelectionChange(rows: Material[]) {
  selectedIds.value = rows.map(r => r.id)
}

async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条素材？`, '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  try {
    await apiMaterials.batchDelete(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    loadMaterials()
  } catch {
    // interceptor handles
  }
}

async function batchClassify() {
  if (!batchDocType.value || !selectedIds.value.length) return
  try {
    await apiMaterials.batchClassify(selectedIds.value, batchDocType.value)
    ElMessage.success('分类已更新')
    batchDocType.value = ''
    selectedIds.value = []
    loadMaterials()
  } catch {
    // interceptor handles
  }
}

function formatDate(value: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

onUnmounted(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
})

onMounted(loadMaterials)
</script>

<style scoped>
.material-manager { padding: 24px; }
.header { display: flex; justify-content: space-between; align-items: center; }
.page-title-wrap { display: flex; flex-direction: column; gap: 6px; }
.page-title { margin: 0; font-size: 22px; font-weight: 700; color: var(--el-text-color-primary); }
.page-subtitle { margin: 0; font-size: 13px; color: var(--el-text-color-secondary); }
.filters { margin-top: 16px; display: flex; align-items: center; }
.keyword-input { width: 240px; margin-left: 12px; }
.batch-actions {
  margin-top: 12px; display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; background: var(--el-color-warning-light-9);
  border-radius: 8px; border: 1px solid var(--el-color-warning-light-5);
}
.batch-actions span { font-size: 13px; color: var(--el-color-warning); font-weight: 500; }
.material-table { margin-top: 16px; border-radius: 8px; overflow: hidden; }
.empty-state { padding: 40px; text-align: center; color: var(--el-text-color-secondary); }
.empty-state p { margin: 12px 0 0; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }

@media (max-width: 768px) {
  .material-manager { padding: 16px; }
  .header { flex-direction: column; align-items: stretch; gap: 12px; }
  .filters { flex-direction: column; align-items: stretch; gap: 8px; }
  .keyword-input { margin-left: 0; width: 100%; }
}
</style>

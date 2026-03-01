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
      <el-select v-model="batchDocType" placeholder="批量分类" size="small" class="batch-type-select">
        <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button size="small" @click="batchClassify" :disabled="!batchDocType">应用分类</el-button>
    </div>

    <el-table
      :data="materials"
      v-loading="loading"
      class="material-table"
      @selection-change="onSelectionChange"
    >
      <template #empty>
        <div class="empty-state">
          <el-icon :size="40" color="#c0c4cc"><Document /></el-icon>
          <p>暂无素材，点击右上角上传</p>
        </div>
      </template>

      <el-table-column type="selection" width="45" />
      <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="doc_type" label="类型" width="120">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.doc_type || '未分类' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="char_count" label="字数" width="90" align="right" />
      <el-table-column label="上传时间" width="190">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import apiMaterials from '@/api/modules/materials'
import { useUserStore } from '@/store/modules/user'
import type { Material, MaterialListParams } from '@/types/writer'
import dayjs from '@/utils/dayjs'
import { DOC_TYPES } from '@/utils/constants'

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
const uploadHeaders = computed(() => (userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}))

const filters = reactive({
  docType: '',
  keyword: '',
})

const MAX_FILE_SIZE = 50 * 1024 * 1024

async function loadMaterials() {
  loading.value = true
  try {
    const params: MaterialListParams = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    if (filters.docType) {
      params.doc_type = filters.docType
    }
    if (filters.keyword.trim()) {
      params.keyword = filters.keyword.trim()
    }

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
  void loadMaterials()
}

function onSearchInput() {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    resetAndLoad()
  }, 400)
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  void loadMaterials()
}

function beforeUpload(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['docx', 'pdf', 'txt'].includes(ext || '')) {
    ElMessage.error('仅支持 .docx/.pdf/.txt 格式')
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

function onUploadProgress() {
  uploading.value = true
}

function onUploadSuccess() {
  uploading.value = false
  ElMessage.success('上传成功，正在解析素材')
  resetAndLoad()
}

function onUploadError() {
  uploading.value = false
  ElMessage.error('上传失败，请稍后重试')
}

function showDetail(row: Material) {
  const keywords = (row.keywords || []).join('、')
  ElMessageBox.alert(
    `类型：${row.doc_type || '未分类'}\n摘要：${row.summary || '无'}\n关键词：${keywords || '无'}`,
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
  } catch {
    return
  }

  try {
    await apiMaterials.delete(id)
    ElMessage.success('删除成功')
    void loadMaterials()
  } catch {
    // handled by interceptor
  }
}

function onSelectionChange(rows: Material[]) {
  selectedIds.value = rows.map(row => row.id)
}

async function batchDelete() {
  if (!selectedIds.value.length) {
    return
  }

  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条素材？`, '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await apiMaterials.batchDelete(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    void loadMaterials()
  } catch {
    // handled by interceptor
  }
}

async function batchClassify() {
  if (!batchDocType.value || !selectedIds.value.length) {
    return
  }

  try {
    await apiMaterials.batchClassify(selectedIds.value, batchDocType.value)
    ElMessage.success('分类更新成功')
    batchDocType.value = ''
    selectedIds.value = []
    void loadMaterials()
  } catch {
    // handled by interceptor
  }
}

function formatDate(value: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

onMounted(() => {
  void loadMaterials()
})

onUnmounted(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
})
</script>

<style scoped>
.material-manager {
  padding: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
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
  color: var(--el-text-color-primary);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.filters {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.keyword-input {
  width: 280px;
}

.batch-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--el-color-warning-light-9);
  border-radius: 8px;
  border: 1px solid var(--el-color-warning-light-5);
}

.batch-actions span {
  font-size: 13px;
  color: var(--el-color-warning);
  font-weight: 500;
}

.batch-type-select {
  width: 120px;
}

.material-table {
  margin-top: 16px;
  border-radius: 8px;
  overflow: hidden;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--el-text-color-secondary);
}

.empty-state p {
  margin: 12px 0 0;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .material-manager {
    padding: 16px;
  }

  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .filters {
    flex-direction: column;
    align-items: stretch;
  }

  .keyword-input {
    width: 100%;
  }

  .batch-actions {
    flex-wrap: wrap;
  }
}
</style>

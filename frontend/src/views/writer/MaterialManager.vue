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
        :data="uploadData"
        :on-success="onUploadSuccess"
        :on-error="onUploadError"
        :on-progress="onUploadProgress"
        :before-upload="beforeUpload"
        :show-file-list="false"
        accept=".doc,.docx,.pdf,.txt"
      >
        <el-button type="primary" :loading="uploadDialogVisible">
          {{ parsing ? '解析中...' : (uploading ? '上传中...' : '上传素材') }}
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

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传与解析进度"
      width="420px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      align-center
    >
      <p class="upload-dialog-text">{{ parseStageText }}</p>
      <el-progress :percentage="combinedPercent" :stroke-width="8" />
      <p class="upload-dialog-subtext">{{ combinedDetailText }}</p>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import apiMaterials from '@/api/modules/materials'
import { useUserStore } from '@/store/modules/user'
import type { Material, MaterialListParams } from '@/types/writer'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import { DOC_TYPES } from '@/utils/constants'

const userStore = useUserStore()

const materials = ref<Material[]>([])
const loading = ref(false)
const uploading = ref(false)
const parsing = ref(false)
const uploadDialogVisible = ref(false)
const uploadPercent = ref(0)
const parsePercent = ref(0)
const parseStageText = ref('等待上传')
const currentUploadTaskId = ref('')
const uploadFlowEnded = ref(false)

const selectedIds = ref<number[]>([])
const batchDocType = ref('')

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let searchTimer: ReturnType<typeof setTimeout> | null = null
let uploadTaskPollTimer: ReturnType<typeof setInterval> | null = null
let pollingTask = false

const uploadUrl = apiMaterials.uploadUrl
const uploadHeaders = computed(() => (userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}))
const uploadData = computed(() => ({
  task_id: currentUploadTaskId.value,
}))
const combinedPercent = computed(() =>
  Math.max(0, Math.min(100, Math.round(uploadPercent.value * 0.5 + parsePercent.value * 0.5))),
)
const combinedDetailText = computed(() => `上传 ${uploadPercent.value}% · 解析 ${parsePercent.value}%`)

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

function generateTaskId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `task-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function stopUploadTaskPolling() {
  if (uploadTaskPollTimer) {
    clearInterval(uploadTaskPollTimer)
    uploadTaskPollTimer = null
  }
}

function startUploadTaskPolling() {
  stopUploadTaskPolling()
  uploadTaskPollTimer = setInterval(() => {
    void pollUploadTask()
  }, 500)
}

async function pollUploadTask() {
  if (!currentUploadTaskId.value || uploadFlowEnded.value || pollingTask) {
    return
  }

  pollingTask = true
  try {
    const { data } = await apiMaterials.getUploadTask(currentUploadTaskId.value)
    parsePercent.value = Math.max(parsePercent.value, Math.max(0, Math.min(100, Number(data.parse_progress || 0))))
    parseStageText.value = data.stage || parseStageText.value
    parsing.value = data.status === 'parsing' || parsePercent.value < 100
  } catch {
    // 任务尚未创建或网络瞬时失败时忽略，下次轮询继续
  } finally {
    pollingTask = false
  }
}

function finishUploadFlow() {
  stopUploadTaskPolling()
  uploadDialogVisible.value = false
  uploading.value = false
  parsing.value = false
  currentUploadTaskId.value = ''
}

function failUploadFlow(message: string) {
  if (uploadFlowEnded.value) {
    return
  }
  uploadFlowEnded.value = true
  finishUploadFlow()
  ElMessage.error(message)
}

function beforeUpload(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['doc', 'docx', 'pdf', 'txt'].includes(ext || '')) {
    ElMessage.error('仅支持 .doc/.docx/.pdf/.txt 格式')
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  uploadFlowEnded.value = false
  currentUploadTaskId.value = generateTaskId()
  uploadPercent.value = 0
  parsePercent.value = 0
  parseStageText.value = '正在上传文件...'
  uploadDialogVisible.value = true
  uploading.value = true
  parsing.value = false
  startUploadTaskPolling()
  return true
}

function onUploadProgress(event: { percent?: number }) {
  const percent = Number(event?.percent || 0)
  if (!Number.isFinite(percent)) {
    return
  }

  uploadPercent.value = Math.max(0, Math.min(100, Math.round(percent)))
  if (uploadPercent.value >= 100) {
    uploading.value = false
    parsing.value = true
    parseStageText.value = '文件上传完成，正在解析素材...'
    return
  }

  uploading.value = true
}

function onUploadSuccess() {
  if (uploadFlowEnded.value) {
    return
  }
  uploadFlowEnded.value = true
  uploadPercent.value = 100
  parsePercent.value = 100
  parseStageText.value = '解析完成'
  finishUploadFlow()
  ElMessage.success('上传成功')
  resetAndLoad()
}

function onUploadError() {
  const wasParsing = parsePercent.value > 0 || uploadPercent.value >= 100 || parsing.value
  failUploadFlow(wasParsing ? '素材解析失败，请稍后重试' : '上传失败，请稍后重试')
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
  return value ? dayjs(value).tz(SHANGHAI_TZ).format('YYYY-MM-DD HH:mm') : '-'
}

onMounted(() => {
  void loadMaterials()
})

onUnmounted(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
  stopUploadTaskPolling()
})
</script>

<style scoped>
.material-manager {
  padding: 24px;
  color: var(--w-color-black);
  background: linear-gradient(180deg, var(--w-color-white) 0%, var(--w-gray-50) 100%);
}

.material-manager :deep(.el-input__wrapper),
.material-manager :deep(.el-select__wrapper) {
  border-radius: var(--w-radius-md);
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
  color: var(--w-color-black);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--w-gray-600);
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
  background: var(--w-gray-50);
  border-radius: var(--w-radius-md);
  border: 1px solid var(--w-gray-200);
  box-shadow: var(--w-shadow-xs);
}

.batch-actions span {
  font-size: 13px;
  color: var(--w-gray-700);
  font-weight: 500;
}

.batch-type-select {
  width: 120px;
}

.material-table {
  margin-top: 16px;
  border: 1px solid var(--w-gray-200);
  border-radius: var(--w-radius-md);
  background: var(--w-color-white);
  box-shadow: var(--w-shadow-xs);
  overflow: hidden;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--w-gray-600);
}

.empty-state p {
  margin: 12px 0 0;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.upload-dialog-text {
  margin: 4px 0 12px;
  color: var(--w-gray-700);
  font-size: 14px;
}

.upload-dialog-subtext {
  margin: 10px 0 0;
  color: var(--w-gray-600);
  font-size: 12px;
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


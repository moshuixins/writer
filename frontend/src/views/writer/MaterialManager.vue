<script setup lang="ts">
import type { Material, MaterialListParams } from '@/types/writer'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import apiMaterials from '@/api/modules/materials'
import ActionBar from '@/components/ActionBar/index.vue'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
import MetaTag from '@/components/MetaTag/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import { useUserStore } from '@/store/modules/user'
import { DOC_TYPE_GROUPS } from '@/utils/constants'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'

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

interface UploadErrorLike extends Error {
  response?: string | { detail?: string }
  status?: number
}

function resolveUploadErrorMessage(error?: UploadErrorLike | null) {
  const response = error?.response
  if (typeof response === 'string') {
    try {
      const parsed = JSON.parse(response) as { detail?: string }
      if (parsed.detail) {
        return parsed.detail
      }
    }
    catch {
      // ignore invalid response bodies
    }
  }
  else if (response?.detail) {
    return response.detail
  }

  if (error?.message) {
    return error.message
  }

  return ''
}

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
  }
  catch {
    materials.value = []
    total.value = 0
  }
  finally {
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
  }
  catch {
    // 任务尚未创建或网络瞬时失败时忽略，下次轮询继续
  }
  finally {
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
  parseStageText.value = '正在上传文件…'
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
    parseStageText.value = '文件上传完成，正在解析素材…'
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

function onUploadError(error?: UploadErrorLike) {
  const wasParsing = parsePercent.value > 0 || uploadPercent.value >= 100 || parsing.value
  const serverMessage = resolveUploadErrorMessage(error)
  failUploadFlow(serverMessage || (wasParsing ? '素材解析失败，请稍后重试' : '上传失败，请稍后重试'))
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
  }
  catch {
    return
  }

  try {
    await apiMaterials.delete(id)
    ElMessage.success('删除成功')
    void loadMaterials()
  }
  catch {
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
  }
  catch {
    return
  }

  try {
    await apiMaterials.batchDelete(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    void loadMaterials()
  }
  catch {
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
  }
  catch {
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

<template>
  <PageShell>
    <PageHeader
      title="素材管理"
      subtitle="上传并管理历史公文素材，用于检索增强、风格分析和写作参考。"
    >
      <template #actions>
        <el-button :loading="loading" @click="resetAndLoad">
          刷新列表
        </el-button>
        <el-upload
          class="material-upload"
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :on-progress="onUploadProgress"
          :before-upload="beforeUpload"
          name="file"
          :show-file-list="false"
          accept=".doc,.docx,.pdf,.txt"
        >
          <el-button type="primary" :loading="uploadDialogVisible">
            {{ parsing ? '解析中…' : (uploading ? '上传中…' : '上传素材') }}
          </el-button>
        </el-upload>
      </template>
    </PageHeader>

    <ActionBar>
      <el-select v-model="filters.docType" class="filter-select" placeholder="按文种筛选" clearable @change="resetAndLoad">
        <el-option-group
          v-for="group in DOC_TYPE_GROUPS"
          :key="group.id"
          :label="group.label"
        >
          <el-option v-for="type in group.options" :key="type" :label="type" :value="type" />
        </el-option-group>
      </el-select>
      <el-input
        v-model="filters.keyword"
        class="keyword-input"
        placeholder="按标题或关键词搜索"
        clearable
        @input="onSearchInput"
        @clear="resetAndLoad"
      />
      <span class="material-summary">共 {{ total }} 条素材</span>
    </ActionBar>

    <ActionBar v-if="selectedIds.length > 0" muted class="batch-bar">
      <span class="material-summary">已选 {{ selectedIds.length }} 项</span>
      <el-select v-model="batchDocType" class="batch-type-select" placeholder="批量设置文种">
        <el-option-group
          v-for="group in DOC_TYPE_GROUPS"
          :key="group.id"
          :label="group.label"
        >
          <el-option v-for="type in group.options" :key="type" :label="type" :value="type" />
        </el-option-group>
      </el-select>
      <el-button :disabled="!batchDocType" @click="batchClassify">
        应用分类
      </el-button>
      <el-button type="danger" @click="batchDelete">
        批量删除
      </el-button>
    </ActionBar>

    <PanelCard
      title="素材列表"
      subtitle="仅展示结构化后的账户素材，书籍学习记录不会出现在这里。"
    >
      <DataTableShell>
        <el-table
          v-loading="loading"
          :data="materials"
          @selection-change="onSelectionChange"
        >
          <template #empty>
            <EmptyState
              icon="i-ep:document"
              title="暂无素材"
              description="支持上传 doc、docx、pdf 和 txt 文件，解析完成后会出现在这里。"
            />
          </template>

          <el-table-column type="selection" width="45" />
          <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
          <el-table-column prop="doc_type" label="文种" width="140">
            <template #default="{ row }">
              <MetaTag :label="row.doc_type || '未分类'" tone="muted" />
            </template>
          </el-table-column>
          <el-table-column prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
          <el-table-column prop="char_count" label="字数" width="90" align="right" />
          <el-table-column label="上传时间" width="190">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button text size="small" @click="showDetail(row)">
                  查看详情
                </el-button>
                <el-button text size="small" @click="deleteMaterial(row.id)">
                  删除
                </el-button>
              </div>
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
          @current-change="loadMaterials"
          @size-change="onPageSizeChange"
        />
      </div>
    </PanelCard>

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传与解析进度"
      width="440px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      align-center
    >
      <div class="upload-progress-panel">
        <div class="upload-progress-panel__stage">
          {{ parseStageText }}
        </div>
        <el-progress :percentage="combinedPercent" :stroke-width="8" />
        <div class="upload-progress-panel__detail">
          {{ combinedDetailText }}
        </div>
      </div>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
.material-upload {
  display: inline-flex;
}

.filter-select {
  width: 220px;
}

.keyword-input {
  width: min(360px, 100%);
}

.batch-type-select {
  width: 220px;
}

.material-summary {
  font-size: 13px;
  color: var(--w-text-secondary);
}

.row-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.upload-progress-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.upload-progress-panel__stage {
  font-size: 14px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.upload-progress-panel__detail {
  font-size: 12px;
  color: var(--w-text-secondary);
}

@media (max-width: 900px) {
  .filter-select,
  .keyword-input,
  .batch-type-select {
    width: 100%;
  }
}
</style>

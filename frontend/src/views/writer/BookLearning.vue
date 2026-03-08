<script setup lang="ts">
import type { BookImportTask, BookScanItem, BookSourceRecord } from '@/types/writer'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import apiBooks from '@/api/modules/books'
import ActionBar from '@/components/ActionBar/index.vue'
import DataTableShell from '@/components/DataTableShell/index.vue'
import EmptyState from '@/components/EmptyState/index.vue'
import MetaTag from '@/components/MetaTag/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import StatusBadge from '@/components/StatusBadge/index.vue'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'

const scanning = ref(false)
const startingImport = ref(false)
const loadingSources = ref(false)

const rebuild = ref(false)
const booksDir = ref('')
const scanItems = ref<BookScanItem[]>([])
const selectedRows = ref<BookScanItem[]>([])
const scanTableRef = ref<any>(null)

const task = ref<BookImportTask | null>(null)
const currentTaskId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const sourceItems = ref<BookSourceRecord[]>([])
const sourceTotal = ref(0)
const sourcePage = ref(1)
const sourceLimit = ref(20)

const allSelected = computed(() => scanItems.value.length > 0 && selectedRows.value.length === scanItems.value.length)
const indeterminate = computed(() => selectedRows.value.length > 0 && selectedRows.value.length < scanItems.value.length)

function statusTone(status: string): 'neutral' | 'success' | 'warning' | 'danger' {
  if (status === 'completed') {
    return 'success'
  }
  if (status === 'partial') {
    return 'warning'
  }
  if (status === 'failed') {
    return 'danger'
  }
  return 'neutral'
}

function formatDate(value?: string | null) {
  if (!value) {
    return '-'
  }
  return dayjs(value).tz(SHANGHAI_TZ).format('YYYY-MM-DD HH:mm:ss')
}

function formatFileSize(size: number) {
  if (!size) {
    return '0 B'
  }
  if (size < 1024) {
    return `${size} B`
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
async function scanBooks() {
  scanning.value = true
  try {
    const { data } = await apiBooks.scan()
    booksDir.value = data.books_dir
    scanItems.value = data.items || []
    selectedRows.value = []
    await nextTick()
    scanTableRef.value?.clearSelection?.()
  }
  catch {
    scanItems.value = []
  }
  finally {
    scanning.value = false
  }
}

function onSelectionChange(rows: BookScanItem[]) {
  selectedRows.value = rows
}

function toggleSelectAll(value: boolean | string | number) {
  const checked = Boolean(value)
  if (!checked) {
    scanTableRef.value?.clearSelection?.()
    selectedRows.value = []
    return
  }
  scanItems.value.forEach((item) => {
    scanTableRef.value?.toggleRowSelection?.(item, true)
  })
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    void pollTask()
  }, 800)
}

async function pollTask() {
  if (!currentTaskId.value) {
    return
  }
  try {
    const { data } = await apiBooks.getTask(currentTaskId.value)
    task.value = data
    if (['completed', 'partial', 'failed'].includes(data.status)) {
      stopPolling()
      await Promise.all([scanBooks(), loadSources()])
      if (data.status === 'completed') {
        ElMessage.success('书籍学习完成')
      }
      else if (data.status === 'partial') {
        ElMessage.warning('书籍学习部分完成，请查看失败项')
      }
      else {
        ElMessage.error(data.message || '书籍学习失败')
      }
    }
  }
  catch {
    stopPolling()
  }
}

async function startImport() {
  if (!scanItems.value.length) {
    return
  }

  const selected = selectedRows.value.length ? selectedRows.value.map(item => item.relative_path) : []
  if (rebuild.value) {
    try {
      await ElMessageBox.confirm(
        '重建会清空已有书籍知识与规则，确认继续？',
        '确认重建',
        {
          type: 'warning',
          confirmButtonText: '确认',
          cancelButtonText: '取消',
        },
      )
    }
    catch {
      return
    }
  }

  startingImport.value = true
  try {
    const { data } = await apiBooks.importBooks({
      rebuild: rebuild.value,
      selected_files: selected,
    })
    currentTaskId.value = data.task_id
    task.value = {
      task_id: data.task_id,
      status: data.status,
      stage: '等待开始',
      message: '',
      rebuild: rebuild.value,
      started_at: Date.now(),
      updated_at: Date.now(),
      finished_at: null,
      total_files: data.total_files,
      completed_files: 0,
      failed_files: 0,
      partial_files: 0,
      skipped_files: 0,
      running_file: '',
      file_progress: 0,
      total_chunks: 0,
      completed_chunks: 0,
      chunk_progress: 0,
      overall_progress: 0,
      ocr_used_files: 0,
      ocr_pages: 0,
      file_results: [],
    }
    startPolling()
    ElMessage.success('书籍学习任务已启动')
  }
  catch {
    ElMessage.error('启动失败，请稍后重试')
  }
  finally {
    startingImport.value = false
  }
}

async function loadSources() {
  loadingSources.value = true
  try {
    const { data } = await apiBooks.listSources({
      skip: (sourcePage.value - 1) * sourceLimit.value,
      limit: sourceLimit.value,
    })
    sourceItems.value = data.items || []
    sourceTotal.value = data.total || 0
  }
  catch {
    sourceItems.value = []
    sourceTotal.value = 0
  }
  finally {
    loadingSources.value = false
  }
}

onMounted(async () => {
  await Promise.all([scanBooks(), loadSources()])
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <PageShell>
    <PageHeader
      title="书籍学习"
      subtitle="扫描并导入 data/book 目录中的 EPUB 与 PDF，提炼写作结构和风格规则进入知识库。"
    >
      <template #actions>
        <el-button :loading="scanning" @click="scanBooks">
          扫描目录
        </el-button>
        <el-button
          type="primary"
          :loading="startingImport"
          :disabled="!scanItems.length"
          @click="startImport"
        >
          开始学习
        </el-button>
      </template>
    </PageHeader>

    <ActionBar>
      <div class="book-learning__meta">
        <span class="book-learning__meta-label">书籍目录</span>
        <code class="book-learning__mono">{{ booksDir || '尚未扫描目录' }}</code>
      </div>
      <div class="book-learning__meta">
        <span class="book-learning__meta-label">导入范围</span>
        <span class="book-learning__meta-value">
          {{ selectedRows.length ? `已选 ${selectedRows.length} 本` : `默认导入全部 ${scanItems.length} 本` }}
        </span>
      </div>
      <el-switch
        v-model="rebuild"
        active-text="重建模式"
        inactive-text="增量模式"
      />
    </ActionBar>

    <PanelCard
      title="扫描结果"
      subtitle="扫描结果只展示书籍源文件，不会进入素材管理列表。"
    >
      <template #actions>
        <el-checkbox
          :model-value="allSelected"
          :indeterminate="indeterminate"
          @change="toggleSelectAll"
        >
          全选
        </el-checkbox>
      </template>

      <DataTableShell>
        <el-table ref="scanTableRef" v-loading="scanning" :data="scanItems" @selection-change="onSelectionChange">
          <template #empty>
            <EmptyState
              icon="i-ep:reading"
              title="还没有扫描到可学习的书籍"
              description="请先把 EPUB 或 PDF 放入 data/book 目录，再点击“扫描目录”。"
            />
          </template>

          <el-table-column type="selection" width="48" />
          <el-table-column prop="source_name" label="文件名" min-width="280" show-overflow-tooltip />
          <el-table-column prop="file_ext" label="格式" width="90" />
          <el-table-column label="大小" width="120">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column label="导入状态" width="120">
            <template #default="{ row }">
              <StatusBadge :label="row.status" :tone="statusTone(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="主文种" min-width="140">
            <template #default="{ row }">
              <MetaTag :label="row.doc_type || '其他'" tone="accent" />
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="190">
            <template #default="{ row }">
              {{ formatDate(row.updated_at) }}
            </template>
          </el-table-column>
        </el-table>
      </DataTableShell>
    </PanelCard>

    <PanelCard
      v-if="task"
      title="学习任务"
      subtitle="展示当前导入任务的阶段、进度与 OCR 使用情况。"
    >
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-card__label">
            当前阶段
          </div>
          <div class="metric-card__value metric-card__value--text">
            {{ task.stage }}
          </div>
          <div class="metric-card__meta">
            {{ task.running_file || '等待调度文件' }}
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-card__label">
            总体进度
          </div>
          <div class="metric-card__value">
            {{ task.overall_progress }}%
          </div>
          <div class="metric-card__meta">
            {{ task.message || '任务进行中' }}
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-card__label">
            文件完成
          </div>
          <div class="metric-card__value">
            {{ task.completed_files }}/{{ task.total_files }}
          </div>
          <div class="metric-card__meta">
            失败 {{ task.failed_files }} · 部分完成 {{ task.partial_files }}
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-card__label">
            OCR 统计
          </div>
          <div class="metric-card__value">
            {{ task.ocr_used_files }}
          </div>
          <div class="metric-card__meta">
            累计识别 {{ task.ocr_pages }} 页
          </div>
        </div>
      </div>

      <div class="book-learning__progress-grid">
        <div class="book-learning__progress-card">
          <div class="book-learning__progress-label">
            总体进度
          </div>
          <el-progress :percentage="task.overall_progress" :stroke-width="8" />
        </div>
        <div class="book-learning__progress-card">
          <div class="book-learning__progress-label">
            文件进度
          </div>
          <el-progress :percentage="task.file_progress" :stroke-width="8" />
          <div class="book-learning__progress-meta">
            {{ task.completed_files }}/{{ task.total_files }}
          </div>
        </div>
        <div class="book-learning__progress-card">
          <div class="book-learning__progress-label">
            分片进度
          </div>
          <el-progress :percentage="task.chunk_progress" :stroke-width="8" />
          <div class="book-learning__progress-meta">
            {{ task.completed_chunks }}/{{ task.total_chunks }}
          </div>
        </div>
      </div>

      <DataTableShell class="book-learning__table-shell">
        <el-table :data="task.file_results" size="small">
          <template #empty>
            <EmptyState title="任务尚未产生文件结果" description="任务启动后会在这里滚动展示各文件学习结果。" />
          </template>

          <el-table-column prop="source_name" label="文件" min-width="220" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <StatusBadge :label="row.status" :tone="statusTone(row.status)" />
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分片数" width="100" align="right" />
          <el-table-column label="OCR" width="120">
            <template #default="{ row }">
              {{ row.ocr_used ? `是（${row.ocr_pages} 页）` : '否' }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="220" show-overflow-tooltip />
        </el-table>
      </DataTableShell>
    </PanelCard>

    <PanelCard
      title="导入记录"
      subtitle="历史导入记录仅作为知识库来源管理，不会出现在素材管理页。"
    >
      <template #actions>
        <el-button :loading="loadingSources" @click="loadSources">
          刷新记录
        </el-button>
      </template>

      <DataTableShell>
        <el-table v-loading="loadingSources" :data="sourceItems">
          <template #empty>
            <EmptyState
              icon="i-ep:collection"
              title="还没有书籍学习记录"
              description="完成一次书籍学习后，这里会展示来源文件、主文种和 OCR 使用情况。"
            />
          </template>

          <el-table-column prop="source_name" label="来源文件" min-width="220" show-overflow-tooltip />
          <el-table-column label="主文种" min-width="140">
            <template #default="{ row }">
              <MetaTag :label="row.doc_type || '其他'" tone="accent" />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <StatusBadge :label="row.status" :tone="statusTone(row.status)" />
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分片数" width="100" align="right" />
          <el-table-column label="OCR" width="90">
            <template #default="{ row }">
              {{ row.ocr_used ? '是' : '否' }}
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="190">
            <template #default="{ row }">
              {{ formatDate(row.updated_at) }}
            </template>
          </el-table-column>
        </el-table>
      </DataTableShell>

      <div v-if="sourceTotal > sourceLimit" class="table-pagination">
        <el-pagination
          v-model:current-page="sourcePage"
          v-model:page-size="sourceLimit"
          :total="sourceTotal"
          layout="total, prev, pager, next"
          @current-change="loadSources"
        />
      </div>
    </PanelCard>
  </PageShell>
</template>

<style scoped>
.book-learning__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.book-learning__meta-label {
  font-size: 12px;
  color: var(--w-text-tertiary);
  white-space: nowrap;
}

.book-learning__meta-value {
  font-size: 13px;
  color: var(--w-text-secondary);
}

.book-learning__meta :deep(.el-switch) {
  margin-left: auto;
}

.book-learning__mono {
  max-width: 100%;
  padding: 4px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--w-text-primary);
  white-space: nowrap;
  background: var(--w-gray-100);
  border-radius: var(--w-radius-sm);
}

.book-learning__progress-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.book-learning__progress-card {
  padding: 16px;
  background: linear-gradient(180deg, #fffdf9 0%, #f7f3eb 100%);
  border: 1px solid var(--w-divider);
  border-radius: 16px;
}

.book-learning__progress-label {
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--w-text-secondary);
}

.book-learning__progress-meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--w-text-tertiary);
}

.metric-card__value--text {
  font-size: 16px;
  line-height: 1.5;
}

.book-learning__table-shell {
  margin-top: 16px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .book-learning__progress-grid {
    grid-template-columns: 1fr;
  }

  .book-learning__meta {
    width: 100%;
  }
}
</style>

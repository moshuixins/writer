<template>
  <div class="book-learning">
    <div class="page-header">
      <div class="title-wrap">
        <h2 class="page-title">书籍学习</h2>
        <p class="page-subtitle">扫描并导入 `data/book` 的 EPUB / PDF，提炼写作规则进入知识库。</p>
      </div>
      <div class="actions">
        <el-button :loading="scanning" @click="scanBooks">扫描书籍</el-button>
        <el-button type="primary" :loading="startingImport" :disabled="!scanItems.length" @click="startImport">
          开始学习
        </el-button>
      </div>
    </div>

    <div class="control-row">
      <el-tag type="info">目录：{{ booksDir || '-' }}</el-tag>
      <el-switch
        v-model="rebuild"
        active-text="重建模式（清空旧书籍知识）"
        inactive-text="增量模式"
      />
    </div>

    <el-card shadow="never" class="scan-card">
      <template #header>
        <div class="card-header">
          <span>扫描结果（{{ scanItems.length }}）</span>
          <el-checkbox
            :model-value="allSelected"
            :indeterminate="indeterminate"
            @change="toggleSelectAll"
          >
            全选
          </el-checkbox>
        </div>
      </template>
      <el-table ref="scanTableRef" :data="scanItems" v-loading="scanning" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="source_name" label="文件名" min-width="280" />
        <el-table-column prop="file_ext" label="格式" width="90" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="导入状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="doc_type" label="文种" width="120" />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="task" shadow="never" class="task-card">
      <template #header>
        <div class="card-header">
          <span>学习任务进度</span>
          <el-tag size="small" :type="statusTagType(task.status)">{{ task.status }}</el-tag>
        </div>
      </template>
      <div class="task-grid">
        <div class="task-item">
          <div class="task-label">当前阶段</div>
          <div class="task-value">{{ task.stage }} {{ task.running_file ? `- ${task.running_file}` : '' }}</div>
        </div>
        <div class="task-item">
          <div class="task-label">总体进度</div>
          <el-progress :percentage="task.overall_progress" :stroke-width="8" />
        </div>
        <div class="task-item">
          <div class="task-label">文件进度</div>
          <el-progress :percentage="task.file_progress" :stroke-width="8" />
          <div class="task-hint">{{ task.completed_files }}/{{ task.total_files }}</div>
        </div>
        <div class="task-item">
          <div class="task-label">分片进度</div>
          <el-progress :percentage="task.chunk_progress" :stroke-width="8" />
          <div class="task-hint">{{ task.completed_chunks }}/{{ task.total_chunks }}</div>
        </div>
        <div class="task-item">
          <div class="task-label">OCR统计</div>
          <div class="task-value">文件 {{ task.ocr_used_files }} / 页数 {{ task.ocr_pages }}</div>
        </div>
      </div>
      <el-table :data="task.file_results" size="small" class="result-table">
        <el-table-column prop="source_name" label="文件" min-width="220" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="chunk_count" label="分片" width="90" />
        <el-table-column label="OCR" width="100">
          <template #default="{ row }">{{ row.ocr_used ? `是(${row.ocr_pages})` : '否' }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-card shadow="never" class="source-card">
      <template #header>
        <div class="card-header">
          <span>导入记录</span>
          <el-button link @click="loadSources">刷新</el-button>
        </div>
      </template>
      <el-table :data="sourceItems" v-loading="loadingSources">
        <el-table-column prop="source_name" label="来源文件" min-width="220" />
        <el-table-column prop="doc_type" label="主文种" width="120" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="chunk_count" label="分片数" width="90" />
        <el-table-column label="OCR" width="90">
          <template #default="{ row }">{{ row.ocr_used ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination" v-if="sourceTotal > sourceLimit">
        <el-pagination
          v-model:current-page="sourcePage"
          v-model:page-size="sourceLimit"
          :total="sourceTotal"
          layout="total, prev, pager, next"
          @current-change="loadSources"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import apiBooks from '@/api/modules/books'
import type { BookImportTask, BookScanItem, BookSourceRecord } from '@/types/writer'

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

function statusTagType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'partial') return 'warning'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'primary'
  return 'info'
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return dayjs(value).tz(SHANGHAI_TZ).format('YYYY-MM-DD HH:mm:ss')
}

function formatFileSize(size: number) {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
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
  } catch {
    scanItems.value = []
  } finally {
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
  if (!currentTaskId.value) return
  try {
    const { data } = await apiBooks.getTask(currentTaskId.value)
    task.value = data
    if (['completed', 'partial', 'failed'].includes(data.status)) {
      stopPolling()
      await Promise.all([scanBooks(), loadSources()])
      if (data.status === 'completed') {
        ElMessage.success('书籍学习完成')
      } else if (data.status === 'partial') {
        ElMessage.warning('书籍学习部分完成，请查看失败项')
      } else {
        ElMessage.error(data.message || '书籍学习失败')
      }
    }
  } catch {
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
    } catch {
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
  } catch {
    ElMessage.error('启动失败，请稍后重试')
  } finally {
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
  } catch {
    sourceItems.value = []
    sourceTotal.value = 0
  } finally {
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

<style scoped>
.book-learning {
  padding: 24px;
  color: var(--w-color-black);
  background: linear-gradient(180deg, var(--w-color-white) 0%, var(--w-gray-50) 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.page-subtitle {
  margin: 0;
  color: var(--w-gray-600);
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
}

.control-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.scan-card,
.task-card,
.source-card {
  border-radius: var(--w-radius-md);
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.task-item {
  border: 1px solid var(--w-gray-200);
  background: var(--w-color-white);
  border-radius: var(--w-radius-md);
  padding: 10px 12px;
}

.task-label {
  font-size: 12px;
  color: var(--w-gray-600);
  margin-bottom: 4px;
}

.task-value {
  color: var(--w-color-black);
  font-size: 13px;
  font-weight: 500;
}

.task-hint {
  margin-top: 4px;
  color: var(--w-gray-600);
  font-size: 12px;
}

.result-table {
  margin-top: 10px;
}

.pagination {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .book-learning {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .actions {
    justify-content: flex-end;
  }

  .task-grid {
    grid-template-columns: 1fr;
  }
}
</style>

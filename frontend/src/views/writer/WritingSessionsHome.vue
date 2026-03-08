<script setup lang="ts">
import type { ChatSession } from '@/types/writer'
import { ElMessage, ElMessageBox } from 'element-plus'
import ActionBar from '@/components/ActionBar/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import { DOC_TYPE_GROUPS } from '@/utils/constants'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import WritingSessionSidebar from './components/WritingSessionSidebar.vue'
import { useWritingSessions } from './useWritingSessions'

const router = useRouter()
const {
  createSession,
  filteredSessions,
  lastOpenedSession,
  loadingSessions,
  loadSessions,
  rememberLastSession,
  removeSession,
  sessionKeyword,
  sessions,
  setKeyword,
  updateSessionTitle,
} = useWritingSessions()

const showNewSession = ref(false)
const newTitle = ref('')
const newDocType = ref('')
const creating = ref(false)

const filteredCount = computed(() => filteredSessions.value.length)

function formatDate(value?: string | null) {
  return value ? dayjs(value).tz(SHANGHAI_TZ).format('MM-DD HH:mm') : '-'
}

async function openSession(session: ChatSession) {
  rememberLastSession(session.id)
  await router.push({
    name: 'writerWorkspace',
    params: { sessionId: session.id },
  })
}

async function continueLastSession() {
  if (!lastOpenedSession.value) {
    return
  }
  await openSession(lastOpenedSession.value)
}

function openNewSessionDialog() {
  showNewSession.value = true
}

async function submitCreateSession() {
  if (!newTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  creating.value = true
  try {
    const session = await createSession({
      title: newTitle.value.trim(),
      doc_type: newDocType.value || null,
    })

    showNewSession.value = false
    newTitle.value = ''
    newDocType.value = ''
    await openSession(session)
  }
  catch {
    ElMessage.error('创建失败，请稍后重试')
  }
  finally {
    creating.value = false
  }
}

async function renameSession(session: ChatSession) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话标题', '重命名会话', {
      inputValue: session.title,
      inputPlaceholder: '请输入会话标题',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (current) => {
        if (!current || !current.trim()) {
          return '标题不能为空'
        }
        if (current.trim().length > 50) {
          return '标题不能超过 50 个字符'
        }
        return true
      },
    })

    const title = value.trim()
    if (title === session.title) {
      return
    }

    await updateSessionTitle(session.id, title)
    ElMessage.success('重命名成功')
  }
  catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error('重命名失败，请稍后重试')
  }
}

async function deleteSession(sessionId: number) {
  try {
    await ElMessageBox.confirm('确定删除该会话？删除后不可恢复。', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  }
  catch {
    return
  }

  try {
    await removeSession(sessionId)
    ElMessage.success('会话已删除')
  }
  catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

onMounted(() => {
  void loadSessions()
})
</script>

<template>
  <PageShell class="page-shell--compact writing-sessions-home">
    <PageHeader
      title="写作会话"
      subtitle="先选择会话，再进入写作工作台继续对话、改写和正文编辑。"
    >
      <template #actions>
        <el-button v-if="lastOpenedSession" @click="continueLastSession">
          继续最近会话
        </el-button>
        <el-button type="primary" @click="openNewSessionDialog">
          新建会话
        </el-button>
      </template>
    </PageHeader>

    <ActionBar muted>
      <span>会话总数：{{ sessions.length }}</span>
      <span>当前筛选：{{ filteredCount }}</span>
      <span v-if="lastOpenedSession">最近会话：{{ lastOpenedSession.title }}</span>
      <span v-else>最近会话：暂无</span>
    </ActionBar>

    <PanelCard
      title="会话列表"
      :subtitle="sessions.length ? '可从列表进入任一写作工作台，搜索条件会保留在当前浏览器会话中。' : '还没有写作会话，可直接从右上角创建。'"
      class="writing-sessions-home__panel"
    >
      <WritingSessionSidebar
        :sessions="sessions"
        :filtered-sessions="filteredSessions"
        :current-session-id="lastOpenedSession?.id ?? null"
        :loading="loadingSessions"
        :keyword="sessionKeyword"
        :format-date="formatDate"
        :show-create-button="false"
        @update:keyword="setKeyword"
        @select="openSession"
        @rename="renameSession"
        @delete="deleteSession"
      />
    </PanelCard>

    <el-dialog v-model="showNewSession" title="新建写作会话" width="420px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="例如：关于开展交通整治的通知" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="公文类型">
          <el-select v-model="newDocType" placeholder="请选择公文类型" class="writing-sessions-home__doc-type-select">
            <el-option-group
              v-for="group in DOC_TYPE_GROUPS"
              :key="group.id"
              :label="group.label"
            >
              <el-option v-for="type in group.options" :key="type" :label="type" :value="type" />
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="writing-sessions-home__dialog-actions">
          <el-button @click="showNewSession = false">
            取消
          </el-button>
          <el-button type="primary" :loading="creating" @click="submitCreateSession">
            创建会话
          </el-button>
        </div>
      </template>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
.writing-sessions-home {
  height: 100%;
  min-height: 0;
}

.writing-sessions-home__panel {
  min-height: 0;
}

.writing-sessions-home__panel :deep(.el-card__body) {
  min-height: 560px;
}

.writing-sessions-home__doc-type-select {
  width: 100%;
}

.writing-sessions-home__dialog-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .writing-sessions-home__panel :deep(.el-card__body) {
    min-height: auto;
  }
}
</style>

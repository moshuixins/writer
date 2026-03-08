<script setup lang="ts">
import type { ChatSession } from '@/types/writer'
import { ElMessage, ElMessageBox } from 'element-plus'
import MetaTag from '@/components/MetaTag/index.vue'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import WritingComposer from './components/WritingComposer.vue'
import WritingEditorPane from './components/WritingEditorPane.vue'
import WritingMessageList from './components/WritingMessageList.vue'
import WritingMobileSwitch from './components/WritingMobileSwitch.vue'
import WritingSessionSidebar from './components/WritingSessionSidebar.vue'
import { useWritingSessions } from './useWritingSessions'
import { useWritingWorkspace } from './useWritingWorkspace'

const route = useRoute()
const router = useRouter()
const {
  filteredSessions,
  loadingSessions,
  loadSessions,
  removeSession,
  sessionKeyword,
  sessions,
  setKeyword,
  updateSessionTitle,
} = useWritingSessions()
const {
  appendSelectionToInput,
  copyContent,
  currentSession,
  draft,
  editorRef,
  exportDoc,
  inputText,
  insertAssistantMessage,
  isMobile,
  lastSavedAt,
  loadingDraft,
  loadingMessages,
  manualSave,
  messages,
  messagesRef,
  mobileTab,
  openSessionById,
  prepareRouteChange,
  renderContent,
  resetWorkspace,
  saveState,
  saveStatusText,
  sendMessage,
  sending,
  skipNextLeaveFlush,
  skipNextRouteLeaveFlush,
  stopGenerating,
} = useWritingWorkspace()

void editorRef
void messagesRef

const sessionDrawerOpen = ref(false)
const loadingWorkspace = ref(true)

const sessionId = computed(() => Number(route.params.sessionId || 0))
const workspaceSubtitle = computed(() => {
  if (!currentSession.value) {
    return '加载当前会话的消息、工作流和文稿草稿。'
  }
  const segments = [`文种：${currentSession.value.doc_type || '未设置'}`]
  if (lastSavedAt.value) {
    segments.push(`最近保存：${lastSavedAt.value}`)
  }
  return segments.join(' · ')
})

function formatDate(value?: string | null) {
  if (!value) {
    return '-'
  }
  return dayjs(value).tz(SHANGHAI_TZ).format('MM-DD HH:mm')
}

async function ensureWorkspaceReady() {
  loadingWorkspace.value = true
  try {
    await loadSessions()
    const opened = await openSessionById(sessionId.value)
    if (!opened) {
      ElMessage.warning('会话不存在或已删除')
      await router.replace({ name: 'writerChat' })
    }
  }
  catch {
    ElMessage.error('加载会话失败，请稍后重试')
    await router.replace({ name: 'writerChat' })
  }
  finally {
    loadingWorkspace.value = false
  }
}

async function goBackToSessions() {
  await prepareRouteChange({ warnOnFailure: true })
  await router.push({ name: 'writerChat' })
}

async function switchSession(session: ChatSession) {
  if (currentSession.value?.id === session.id) {
    sessionDrawerOpen.value = false
    return
  }
  sessionDrawerOpen.value = false
  await prepareRouteChange({ warnOnFailure: true })
  await router.push({
    name: 'writerWorkspace',
    params: { sessionId: session.id },
  })
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

async function deleteSession(sessionIdToDelete: number) {
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
    const deletingCurrent = Number(currentSession.value?.id) === Number(sessionIdToDelete)
    await removeSession(sessionIdToDelete)
    ElMessage.success('会话已删除')
    if (deletingCurrent) {
      resetWorkspace()
      skipNextRouteLeaveFlush()
      await router.replace({ name: 'writerChat' })
    }
  }
  catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

onBeforeRouteLeave(async () => {
  if (skipNextLeaveFlush.value) {
    skipNextLeaveFlush.value = false
    return true
  }
  await prepareRouteChange()
  return true
})

onMounted(() => {
  void ensureWorkspaceReady()
})
</script>

<template>
  <PageShell class="page-shell--compact writing-workspace-page">
    <PageHeader
      :title="currentSession?.title || '写作工作台'"
      :subtitle="workspaceSubtitle"
    >
      <template #actions>
        <el-button @click="goBackToSessions">
          返回会话列表
        </el-button>
        <el-button type="primary" @click="sessionDrawerOpen = true">
          切换会话
        </el-button>
      </template>
    </PageHeader>

    <WritingMobileSwitch v-if="isMobile && currentSession" v-model="mobileTab" />

    <div class="writing-workspace">
      <section class="writing-workspace__column writing-workspace__column--chat" :class="{ 'is-hidden': isMobile && mobileTab !== 'chat' }">
        <PanelCard class="writing-workspace__panel writing-workspace__panel--chat">
          <template #header>
            <div class="writing-workspace__panel-head">
              <div class="writing-workspace__panel-copy">
                <div class="writing-workspace__panel-kicker">
                  当前任务
                </div>
                <div class="writing-workspace__panel-title">
                  {{ currentSession?.title || '写作工作台' }}
                </div>
                <div class="writing-workspace__panel-meta">
                  <MetaTag :label="currentSession?.doc_type || '未设置文种'" tone="accent" />
                  <span v-if="currentSession">最近 20 条会话上下文持续生效</span>
                  <span v-else>正在加载当前会话</span>
                </div>
              </div>
            </div>
          </template>

          <div ref="messagesRef" class="writing-workspace__messages">
            <WritingMessageList
              :current-session="currentSession"
              :loading="loadingWorkspace || loadingMessages"
              :messages="messages"
              :render-message="renderContent"
              @copy="copyContent"
              @insert="insertAssistantMessage"
            />
          </div>
          <WritingComposer
            v-if="currentSession"
            v-model="inputText"
            :sending="sending"
            :has-session="Boolean(currentSession)"
            @send="sendMessage"
            @stop="stopGenerating"
            @export="exportDoc"
          />
        </PanelCard>
      </section>

      <section class="writing-workspace__column writing-workspace__column--editor" :class="{ 'is-hidden': isMobile && mobileTab !== 'editor' }">
        <PanelCard class="writing-workspace__panel writing-workspace__panel--editor">
          <template #header>
            <div class="writing-workspace__panel-head">
              <div class="writing-workspace__panel-copy">
                <div class="writing-workspace__panel-kicker">
                  文稿面板
                </div>
                <div class="writing-workspace__panel-title">
                  正文草稿
                </div>
                <div class="writing-workspace__panel-meta">
                  <span>与当前会话绑定，支持自动保存和引用选中文本</span>
                </div>
              </div>
            </div>
          </template>

          <WritingEditorPane
            ref="editorRef"
            v-model="draft"
            :current-session="currentSession"
            :loading-draft="loadingWorkspace || loadingDraft"
            :save-status="saveStatusText"
            :saving="saveState === 'saving-auto' || saveState === 'saving-manual'"
            :last-saved-at="lastSavedAt"
            @manual-save="manualSave"
            @quote-selection="appendSelectionToInput"
          />
        </PanelCard>
      </section>
    </div>

    <el-drawer
      v-model="sessionDrawerOpen"
      title="切换会话"
      size="360px"
      append-to-body
      destroy-on-close
    >
      <WritingSessionSidebar
        :sessions="sessions"
        :filtered-sessions="filteredSessions"
        :current-session-id="currentSession?.id ?? null"
        :loading="loadingSessions"
        :keyword="sessionKeyword"
        :format-date="formatDate"
        :show-create-button="false"
        @update:keyword="setKeyword"
        @select="switchSession"
        @rename="renameSession"
        @delete="deleteSession"
      />
    </el-drawer>
  </PageShell>
</template>

<style scoped>
.writing-workspace-page {
  height: 100%;
  min-height: 0;
}

.writing-workspace {
  display: grid;
  grid-template-columns: minmax(760px, 1fr) 480px;
  gap: 18px;
  min-height: 0;
}

.writing-workspace__column {
  min-width: 0;
  min-height: 0;
}

.writing-workspace__column.is-hidden {
  display: none;
}

.writing-workspace__panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.writing-workspace__panel :deep(.el-card__body) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.writing-workspace__panel--chat {
  box-shadow: var(--w-shadow-sm);
}

.writing-workspace__panel--chat :deep(.el-card__body) {
  background: linear-gradient(180deg, rgb(255 253 249 / 100%) 0%, rgb(251 248 242 / 96%) 100%);
}

.writing-workspace__panel--editor :deep(.el-card__body) {
  min-height: 0;
  padding: 16px;
}

.writing-workspace__panel-head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  justify-content: space-between;
}

.writing-workspace__panel-copy {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.writing-workspace__panel-kicker {
  font-size: 11px;
  font-weight: 700;
  color: var(--w-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.writing-workspace__panel-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--w-text-primary);
}

.writing-workspace__panel-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  line-height: 1.6;
  color: var(--w-text-secondary);
}

.writing-workspace__messages {
  flex: 1;
  min-height: 0;
  padding-right: 6px;
  overflow-y: auto;
}

@media (max-width: 1360px) {
  .writing-workspace {
    grid-template-columns: minmax(0, 1fr) 420px;
  }
}

@media (max-width: 900px) {
  .writing-workspace {
    grid-template-columns: 1fr;
  }

  .writing-workspace__panel,
  .writing-workspace__panel--editor :deep(.el-card__body) {
    height: auto;
    min-height: auto;
  }

  .writing-workspace__messages {
    max-height: 52vh;
  }
}
</style>

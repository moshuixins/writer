<script setup lang="ts">
import type { ChatMessage, ChatSession, ChatWorkflowStep, WriterDraft } from '@/types/writer'
import DOMPurify from 'dompurify'

import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '@/api'
import apiChat from '@/api/modules/chat'
import apiDocuments from '@/api/modules/documents'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'
import { useUserStore } from '@/store/modules/user'
import { DOC_TYPE_GROUPS } from '@/utils/constants'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import WritingComposer from './components/WritingComposer.vue'
import WritingEditorPane from './components/WritingEditorPane.vue'
import WritingMessageList from './components/WritingMessageList.vue'
import WritingMobileSwitch from './components/WritingMobileSwitch.vue'
import WritingSessionSidebar from './components/WritingSessionSidebar.vue'

interface OfficialEditorExpose {
  insertTextAtCursor: (text: string) => void
  focusEditor: () => void
}

interface WorkflowEventPayload {
  event?: string
  step?: string
  status?: 'running' | 'done' | 'error'
  detail?: string
}

type SaveState = 'idle' | 'dirty' | 'saving-auto' | 'saving-manual' | 'saved' | 'error'

const userStore = useUserStore()
const md = new MarkdownIt({ breaks: true, linkify: true })

const sessions = ref<ChatSession[]>([])
const currentSession = ref<ChatSession | null>(null)
const messages = ref<ChatMessage[]>([])
const draft = ref<WriterDraft>(createEmptyDraft())

const inputText = ref('')
const sending = ref(false)
const showNewSession = ref(false)
const newTitle = ref('')
const newDocType = ref('')
const creating = ref(false)

const loadingSessions = ref(false)
const loadingMessages = ref(false)
const loadingDraft = ref(false)
const mobileSidebarOpen = ref(false)
const sessionKeyword = ref('')

const isMobile = ref(window.innerWidth <= 900)
const mobileTab = ref<'chat' | 'editor'>('chat')

const messagesRef = ref<HTMLElement>()
const editorRef = ref<OfficialEditorExpose | null>(null)

const saveState = ref<SaveState>('idle')
const draftDirty = ref(false)
const lastSavedAt = ref('')
const hydratingDraft = ref(false)

const abortController = ref<AbortController | null>(null)
let msgIdCounter = 0
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

const filteredSessions = computed(() => {
  const keyword = sessionKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return sessions.value
  }
  return sessions.value.filter(s => (s.title || '').toLowerCase().includes(keyword))
})

const saveStatusText = computed(() => {
  switch (saveState.value) {
    case 'dirty':
      return '未保存'
    case 'saving-auto':
      return '自动保存中'
    case 'saving-manual':
      return '保存中'
    case 'saved':
      return '已保存'
    case 'error':
      return '保存失败'
    default:
      return '草稿未保存'
  }
})

function createEmptyDraft(title = ''): WriterDraft {
  return {
    title,
    recipients: '',
    body_json: {
      type: 'doc',
      content: [{ type: 'paragraph' }],
    },
    signing_org: '',
    date: '',
  }
}

function normalizeDraft(raw: Partial<WriterDraft> | null | undefined, sessionTitle = ''): WriterDraft {
  const body = raw?.body_json
  const bodyJson = (body && typeof body === 'object' && (body as Record<string, unknown>).type === 'doc')
    ? body
    : createEmptyDraft().body_json

  return {
    title: (raw?.title || sessionTitle || '').trim(),
    recipients: (raw?.recipients || '').trim(),
    body_json: bodyJson,
    signing_org: (raw?.signing_org || '').trim(),
    date: (raw?.date || '').trim(),
  }
}

function extractBodyNodeText(node: unknown): string {
  if (!node || typeof node !== 'object') {
    return ''
  }

  const current = node as Record<string, unknown>
  if (current.type === 'text') {
    return typeof current.text === 'string' ? current.text : ''
  }
  if (current.type === 'hardBreak') {
    return '\n'
  }

  const content = Array.isArray(current.content) ? current.content : []
  return content.map(child => extractBodyNodeText(child)).join('')
}

function extractH1TitleFromBody(bodyJson: unknown): string {
  if (!bodyJson || typeof bodyJson !== 'object') {
    return ''
  }

  const content = Array.isArray((bodyJson as Record<string, unknown>).content)
    ? ((bodyJson as Record<string, unknown>).content as unknown[])
    : []

  for (const node of content) {
    if (!node || typeof node !== 'object') {
      continue
    }

    const current = node as Record<string, unknown>
    if (current.type !== 'heading') {
      continue
    }

    const attrs = (current.attrs && typeof current.attrs === 'object')
      ? (current.attrs as Record<string, unknown>)
      : {}
    const level = Number(attrs.level ?? 2)
    if (level !== 1) {
      continue
    }

    const text = extractBodyNodeText(current).trim()
    if (text) {
      return text
    }
  }

  return ''
}

function renderContent(msg: ChatMessage): string {
  if (msg.role !== 'assistant') {
    return ''
  }
  return DOMPurify.sanitize(md.render(msg.content || ''))
}

function normalizeWorkflowStatus(status?: string): 'running' | 'done' | 'error' {
  if (status === 'done' || status === 'error') {
    return status
  }
  return 'running'
}

function upsertWorkflowStep(msg: ChatMessage, payload: WorkflowEventPayload) {
  if (!payload.step) {
    return
  }
  const status = normalizeWorkflowStatus(payload.status)
  const steps = msg.workflow_steps ? [...msg.workflow_steps] : []
  const key = payload.step.trim()
  const idx = steps.findIndex(item => item.step === key)
  if (idx === -1) {
    const step: ChatWorkflowStep = {
      id: `wf-${Date.now()}-${msgIdCounter++}`,
      step: key,
      status,
      detail: payload.detail,
    }
    steps.push(step)
  }
  else {
    steps[idx] = {
      ...steps[idx],
      status,
      detail: payload.detail || steps[idx].detail,
    }
  }
  msg.workflow_steps = steps
}

function copyContent(text: string) {
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.warning('复制失败，请手动复制'),
  )
}

function getStreamUrl() {
  const baseURL = `${api.defaults.baseURL || ''}`.trim()
  if (!baseURL) {
    return '/api/chat/send-stream'
  }
  return `${baseURL.replace(/\/+$/, '')}/api/chat/send-stream`
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function clearAutoSaveTimer() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
}

function scheduleAutoSave() {
  if (!currentSession.value || !draftDirty.value) {
    return
  }

  clearAutoSaveTimer()
  autoSaveTimer = setTimeout(() => {
    void persistDraft('auto', { silent: true })
  }, 5000)
}

async function persistDraft(
  mode: 'auto' | 'manual',
  options: { force?: boolean, silent?: boolean, timeout?: number } = {},
) {
  if (!currentSession.value) {
    return false
  }

  if (!options.force && mode === 'auto' && !draftDirty.value) {
    return true
  }

  saveState.value = mode === 'auto' ? 'saving-auto' : 'saving-manual'

  try {
    const { data } = await apiChat.saveDraft(
      currentSession.value.id,
      {
        save_mode: mode,
        draft: draft.value,
      },
      options.timeout ? { timeout: options.timeout } : undefined,
    )

    if (data?.draft) {
      hydratingDraft.value = true
      draft.value = normalizeDraft(data.draft, currentSession.value.title)
      await nextTick()
      hydratingDraft.value = false
    }

    draftDirty.value = false
    saveState.value = 'saved'
    lastSavedAt.value = data.updated_at ? dayjs(data.updated_at).tz(SHANGHAI_TZ).format('HH:mm:ss') : dayjs().tz(SHANGHAI_TZ).format('HH:mm:ss')
    return true
  }
  catch {
    saveState.value = 'error'
    if (!options.silent) {
      ElMessage.error(mode === 'manual' ? '保存失败，请稍后重试' : '自动保存失败，稍后会继续尝试')
    }
    return false
  }
}

async function manualSave() {
  await persistDraft('manual', { force: true })
}

async function flushDraftBeforeSwitch() {
  if (!currentSession.value || !draftDirty.value) {
    return true
  }
  return persistDraft('auto', { timeout: 2500, silent: true, force: true })
}

watch(
  draft,
  () => {
    if (hydratingDraft.value || !currentSession.value) {
      return
    }
    draftDirty.value = true
    saveState.value = 'dirty'
    scheduleAutoSave()
  },
  { deep: true },
)

async function loadSessions() {
  loadingSessions.value = true
  try {
    const { data } = await apiChat.getSessions()
    sessions.value = data

    if (!currentSession.value && data.length > 0) {
      await selectSession(data[0])
    }
  }
  catch {
    sessions.value = []
  }
  finally {
    loadingSessions.value = false
  }
}

async function selectSession(session: ChatSession) {
  if (currentSession.value?.id === session.id) {
    mobileSidebarOpen.value = false
    return
  }

  const saved = await flushDraftBeforeSwitch()
  if (!saved) {
    ElMessage.warning('上一会话草稿保存失败，已保留本地未保存状态')
  }

  currentSession.value = session
  mobileSidebarOpen.value = false
  loadingMessages.value = true
  loadingDraft.value = true
  mobileTab.value = 'chat'

  try {
    const [messageResp, draftResp] = await Promise.all([
      apiChat.getMessages(session.id),
      apiChat.getDraft(session.id),
    ])

    messages.value = messageResp.data
    scrollToBottom()

    hydratingDraft.value = true
    draft.value = normalizeDraft(draftResp.data.draft, session.title)
    await nextTick()
    hydratingDraft.value = false

    draftDirty.value = false
    saveState.value = draftResp.data.exists ? 'saved' : 'idle'
    lastSavedAt.value = draftResp.data.updated_at ? dayjs(draftResp.data.updated_at).tz(SHANGHAI_TZ).format('HH:mm:ss') : ''
  }
  catch {
    messages.value = []
    hydratingDraft.value = true
    draft.value = createEmptyDraft(session.title)
    await nextTick()
    hydratingDraft.value = false

    draftDirty.value = false
    saveState.value = 'idle'
    lastSavedAt.value = ''
  }
  finally {
    loadingMessages.value = false
    loadingDraft.value = false
  }
}

function openNewSession() {
  showNewSession.value = true
  mobileSidebarOpen.value = false
}

async function createSession() {
  if (!newTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  creating.value = true
  try {
    const { data } = await apiChat.createSession({
      title: newTitle.value.trim(),
      doc_type: newDocType.value || null,
    })

    sessions.value.unshift(data)

    showNewSession.value = false
    newTitle.value = ''
    newDocType.value = ''

    await selectSession(data)
  }
  catch {
    ElMessage.error('创建失败，请稍后重试')
  }
  finally {
    creating.value = false
  }
}

async function sendMessage() {
  if (!currentSession.value || !inputText.value.trim() || sending.value) {
    return
  }

  const text = inputText.value.trim()
  sending.value = true
  inputText.value = ''
  abortController.value = new AbortController()

  const userTempId = `sending-${msgIdCounter++}`
  const assistantTempId = `stream-${msgIdCounter++}`

  messages.value.push({ id: userTempId, role: 'user', content: text })
  const assistantMsg: ChatMessage = { id: assistantTempId, role: 'assistant', content: '', workflow_steps: [] }
  messages.value.push(assistantMsg)
  scrollToBottom()

  try {
    const resp = await fetch(getStreamUrl(), {
      method: 'POST',
      signal: abortController.value.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {}),
      },
      body: JSON.stringify({
        session_id: currentSession.value.id,
        message: text,
      }),
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      throw new Error('读取响应流失败')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    const processLine = (line: string) => {
      if (!line.startsWith('data: ')) {
        return
      }
      const payload = line.slice(6).trim()
      if (!payload || payload === '[DONE]') {
        return
      }
      const parsed = JSON.parse(payload)
      if (parsed.error) {
        throw new Error(parsed.error)
      }
      if (parsed.event === 'workflow') {
        upsertWorkflowStep(assistantMsg, parsed as WorkflowEventPayload)
        const idx = messages.value.findIndex(m => m.id === assistantTempId)
        if (idx !== -1) {
          messages.value[idx] = { ...assistantMsg }
        }
        scrollToBottom()
        return
      }
      if (parsed.chunk) {
        assistantMsg.content += parsed.chunk
        const idx = messages.value.findIndex(m => m.id === assistantTempId)
        if (idx !== -1) {
          messages.value[idx] = { ...assistantMsg }
        }
        scrollToBottom()
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        processLine(line)
      }
    }

    if (buffer.trim()) {
      processLine(buffer.trim())
    }
    if (assistantMsg.content.trim() || assistantMsg.workflow_steps?.length) {
      const idx = messages.value.findIndex(m => m.id === assistantTempId)
      if (idx !== -1) {
        messages.value[idx] = {
          ...assistantMsg,
          id: `assistant-${Date.now()}-${msgIdCounter++}`,
        }
      }
    }
  }
  catch (error: any) {
    if (error?.name === 'AbortError') {
      const idx = messages.value.findIndex(m => m.id === assistantTempId)
      if (idx !== -1 && !assistantMsg.content.trim() && !(assistantMsg.workflow_steps?.length)) {
        messages.value.splice(idx, 1)
      }
      ElMessage.info('已停止生成')
    }
    else {
      messages.value = messages.value.filter(m => m.id !== userTempId && m.id !== assistantTempId)
      inputText.value = text
      ElMessage.error(error?.message || '发送失败，请稍后重试')
    }
  }
  finally {
    abortController.value = null
    sending.value = false
  }
}

function stopGenerating() {
  abortController.value?.abort()
}

function insertAssistantMessage(content: string) {
  if (!currentSession.value) {
    return
  }

  const text = (content || '').trim()
  if (!text.trim()) {
    ElMessage.warning('当前消息内容为空，无法插入')
    return
  }

  editorRef.value?.insertTextAtCursor(text)
  editorRef.value?.focusEditor()
  if (isMobile.value) {
    mobileTab.value = 'editor'
  }
  ElMessage.success('内容已插入文稿')
}

function appendSelectionToInput(selectedText: string) {
  const payload = `【引用文稿片段】\n${selectedText}\n\n请基于以上片段继续修改：`
  inputText.value = inputText.value.trim()
    ? `${inputText.value.trim()}\n\n${payload}`
    : payload

  if (isMobile.value) {
    mobileTab.value = 'chat'
  }
}

async function exportDoc() {
  if (!currentSession.value) {
    return
  }

  clearAutoSaveTimer()
  const saved = await persistDraft('manual', { force: true })
  if (!saved) {
    ElMessage.error('草稿保存失败，导出已取消')
    return
  }

  try {
    const resp = await apiDocuments.exportEditorDoc({
      session_id: currentSession.value.id,
      doc_type: currentSession.value.doc_type || '',
      draft: draft.value,
    })

    const blobUrl = URL.createObjectURL(resp.data)
    const a = window.document.createElement('a')
    a.href = blobUrl
    const exportTitle = extractH1TitleFromBody(draft.value.body_json) || draft.value.title || '文稿'
    a.download = `${exportTitle}.docx`
    a.click()
    URL.revokeObjectURL(blobUrl)

    ElMessage.success('导出成功')
  }
  catch {
    ElMessage.error('导出失败，请稍后重试')
  }
}

async function deleteSession(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该会话？删除后不可恢复', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  }
  catch {
    return
  }

  try {
    const deletingCurrent = Number(currentSession.value?.id) === Number(id)
    await apiChat.deleteSession(id)
    sessions.value = sessions.value.filter(s => Number(s.id) !== Number(id))

    if (deletingCurrent) {
      currentSession.value = null
      messages.value = []
      draft.value = createEmptyDraft()
      saveState.value = 'idle'
      draftDirty.value = false
      lastSavedAt.value = ''
    }

    await loadSessions()
    ElMessage.success('会话已删除')
  }
  catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

async function renameSession(session: ChatSession) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话标题', '重命名会话', {
      inputValue: session.title,
      inputPlaceholder: '请输入会话标题',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (val) => {
        if (!val || !val.trim()) {
          return '标题不能为空'
        }
        if (val.trim().length > 50) {
          return '标题不能超过50个字符'
        }
        return true
      },
    })

    const title = value.trim()
    if (title === session.title) {
      return
    }

    const { data } = await apiChat.updateSession(session.id, { title })
    const index = sessions.value.findIndex(s => s.id === session.id)
    if (index !== -1) {
      sessions.value[index] = { ...sessions.value[index], ...data }
    }
    if (currentSession.value?.id === session.id) {
      currentSession.value = { ...currentSession.value, ...data }
    }

    ElMessage.success('重命名成功')
  }
  catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error('重命名失败，请稍后重试')
  }
}

function formatDate(value: string) {
  return value ? dayjs(value).tz(SHANGHAI_TZ).format('MM-DD HH:mm') : '-'
}

function handleResize() {
  const mobile = window.innerWidth <= 900
  isMobile.value = mobile
  if (!mobile) {
    mobileTab.value = 'chat'
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  void loadSessions()
})

onBeforeUnmount(() => {
  abortController.value?.abort()
  clearAutoSaveTimer()
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <PageShell class="page-shell--compact writing-chat-page">
    <PageHeader
      title="写作对话"
      subtitle="在同一工作区完成会话管理、AI 工作流跟踪和公文正文编辑。"
    >
      <template #actions>
        <el-button class="writing-chat__sidebar-trigger" @click="mobileSidebarOpen = true">
          会话列表
        </el-button>
        <el-button type="primary" @click="openNewSession">
          新建会话
        </el-button>
      </template>
    </PageHeader>

    <WritingMobileSwitch v-if="isMobile && currentSession" v-model="mobileTab" />

    <div class="writing-chat">
      <div v-if="mobileSidebarOpen" class="writing-chat__mask" @click="mobileSidebarOpen = false" />

      <aside class="writing-chat__sidebar" :class="{ 'is-open': mobileSidebarOpen }">
        <WritingSessionSidebar
          :sessions="sessions"
          :filtered-sessions="filteredSessions"
          :current-session-id="currentSession?.id ?? null"
          :loading="loadingSessions"
          :keyword="sessionKeyword"
          :format-date="formatDate"
          @create="openNewSession"
          @update:keyword="sessionKeyword = $event"
          @select="selectSession"
          @rename="renameSession"
          @delete="deleteSession"
        />
      </aside>

      <section class="writing-chat__column" :class="{ 'is-hidden': isMobile && mobileTab !== 'chat' }">
        <PanelCard
          class="writing-chat__panel"
          :title="currentSession ? currentSession.title : '写作对话'"
          :subtitle="currentSession ? (currentSession.doc_type || '未设置文种') : '请先选择或新建会话'"
        >
          <div ref="messagesRef" class="writing-chat__messages">
            <WritingMessageList
              :current-session="currentSession"
              :loading="loadingMessages"
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

      <section class="writing-chat__column" :class="{ 'is-hidden': isMobile && mobileTab !== 'editor' }">
        <PanelCard
          class="writing-chat__panel writing-chat__panel--editor"
          title="正文草稿"
          subtitle="编辑器与当前会话绑定，支持自动保存和引用选中文本。"
        >
          <WritingEditorPane
            ref="editorRef"
            v-model="draft"
            :current-session="currentSession"
            :loading-draft="loadingDraft"
            :save-status="saveStatusText"
            :saving="saveState === 'saving-auto' || saveState === 'saving-manual'"
            :last-saved-at="lastSavedAt"
            @manual-save="manualSave"
            @quote-selection="appendSelectionToInput"
          />
        </PanelCard>
      </section>
    </div>

    <el-dialog v-model="showNewSession" title="新建写作会话" width="420px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="例如：关于开展交通整治的通知" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="公文类型">
          <el-select v-model="newDocType" placeholder="请选择公文类型" class="writing-chat__doc-type-select">
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
        <div class="writing-chat__dialog-actions">
          <el-button @click="showNewSession = false">
            取消
          </el-button>
          <el-button type="primary" :loading="creating" @click="createSession">
            创建会话
          </el-button>
        </div>
      </template>
    </el-dialog>
  </PageShell>
</template>

<style scoped>
.writing-chat-page {
  height: 100%;
  min-height: 0;
}

.writing-chat {
  position: relative;
  display: grid;
  flex: 1;
  grid-template-columns: 320px minmax(0, 1fr) minmax(0, 1.05fr);
  gap: 16px;
  min-height: 0;
}

.writing-chat__mask {
  position: fixed;
  inset: 0;
  z-index: 30;
  background: var(--w-overlay);
}

.writing-chat__sidebar {
  position: relative;
  z-index: 31;
  min-height: 0;
  padding: 16px;
  background: var(--w-panel-bg);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-lg);
  box-shadow: var(--w-shadow-xs);
}

.writing-chat__column {
  min-width: 0;
  min-height: 0;
}

.writing-chat__column.is-hidden {
  display: none;
}

.writing-chat__panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.writing-chat__panel :deep(.el-card__body) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.writing-chat__panel--editor :deep(.el-card__body) {
  min-height: 640px;
}

.writing-chat__messages {
  flex: 1;
  min-height: 0;
  padding-right: 4px;
  overflow-y: auto;
}

.writing-chat__sidebar-trigger {
  display: none;
}

.writing-chat__doc-type-select {
  width: 100%;
}

.writing-chat__dialog-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 1180px) {
  .writing-chat {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .writing-chat__column:last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .writing-chat {
    grid-template-columns: 1fr;
  }

  .writing-chat__sidebar-trigger {
    display: inline-flex;
  }

  .writing-chat__sidebar {
    position: fixed;
    top: 16px;
    bottom: 16px;
    left: 16px;
    width: min(340px, calc(100vw - 32px));
    transform: translateX(calc(-100% - 24px));
    transition: transform 0.24s ease;
  }

  .writing-chat__sidebar.is-open {
    transform: translateX(0);
  }

  .writing-chat__panel,
  .writing-chat__panel--editor :deep(.el-card__body) {
    height: auto;
    min-height: auto;
  }

  .writing-chat__messages {
    max-height: 52vh;
  }
}
</style>

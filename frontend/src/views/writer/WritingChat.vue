<template>
  <div class="writing-chat">
    <div v-if="mobileSidebarOpen" class="sidebar-mask" @click="mobileSidebarOpen = false" />

    <el-button class="mobile-session-trigger" type="primary" circle @click="mobileSidebarOpen = true">
      <el-icon><Menu /></el-icon>
    </el-button>

    <aside class="sidebar" :class="{ 'is-mobile-open': mobileSidebarOpen }">
      <el-button type="primary" @click="openNewSession" class="new-btn">
        <el-icon style="margin-right: 6px"><Plus /></el-icon>
        新建写作
      </el-button>
      <el-input
        v-model="sessionKeyword"
        class="session-search"
        clearable
        placeholder="搜索会话标题"
      />
      <div class="session-list">
        <template v-if="loadingSessions">
          <el-skeleton :rows="4" animated style="padding: 8px" />
        </template>
        <template v-else-if="sessions.length === 0">
          <div class="empty-tip">暂无会话，点击上方新建</div>
        </template>
        <template v-else-if="filteredSessions.length === 0">
          <div class="empty-tip">没有匹配的会话</div>
        </template>
        <button
          v-else
          v-for="s in filteredSessions"
          :key="s.id"
          class="session-item"
          :class="{ active: currentSession?.id === s.id }"
          type="button"
          @click="selectSession(s)"
        >
          <div class="session-info">
            <span class="session-title">{{ s.title }}</span>
            <span class="session-time">{{ formatDate(s.created_at) }}</span>
            <el-tag v-if="s.doc_type" size="small" type="info" class="session-tag">{{ s.doc_type }}</el-tag>
          </div>
          <div class="session-actions">
            <el-icon class="edit-btn" @click.stop="renameSession(s)"><Edit /></el-icon>
            <el-icon class="delete-btn" @click.stop="deleteSession(s.id)"><Close /></el-icon>
          </div>
        </button>
      </div>
    </aside>

    <main class="workspace">
      <div v-if="isMobile && currentSession" class="mobile-tab-toggle">
        <el-radio-group v-model="mobileTab" size="small">
          <el-radio-button label="chat">对话</el-radio-button>
          <el-radio-button label="editor">文稿</el-radio-button>
        </el-radio-group>
      </div>

      <section class="chat-panel" :class="{ hidden: isMobile && mobileTab !== 'chat' }">
        <div class="chat-header" v-if="currentSession">
          <el-button text class="session-toggle-btn" @click="mobileSidebarOpen = true">
            <el-icon><Menu /></el-icon>
          </el-button>
          <h3>{{ currentSession.title }}</h3>
          <el-tag v-if="currentSession.doc_type" size="small">{{ currentSession.doc_type }}</el-tag>
        </div>

        <div class="messages" ref="messagesRef">
          <template v-if="loadingMessages">
            <el-skeleton :rows="4" animated style="padding: 16px" />
          </template>
          <template v-else-if="!currentSession">
            <div class="empty-chat">
              <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
              <p>请先选择或新建会话</p>
            </div>
          </template>
          <template v-else-if="messages.length === 0">
            <div class="empty-chat">
              <el-icon :size="48" color="#c0c4cc"><EditPen /></el-icon>
              <p>输入你的写作需求开始生成</p>
            </div>
          </template>
          <template v-else>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message"
              :class="[msg.role, { sending: msg.id?.toString().startsWith('sending-') || msg.id?.toString().startsWith('stream-') }]"
            >
              <div class="avatar" :class="msg.role">
                <el-icon v-if="msg.role === 'assistant'" :size="18"><Monitor /></el-icon>
                <el-icon v-else :size="18"><User /></el-icon>
              </div>
              <div class="bubble-wrap">
                <div v-if="msg.role === 'assistant' && msg.workflow_steps?.length" class="workflow-card">
                  <div class="workflow-title">AI 工作流程</div>
                  <div
                    v-for="step in msg.workflow_steps"
                    :key="step.id"
                    class="workflow-item"
                    :class="`is-${step.status}`"
                  >
                    <span class="workflow-dot" />
                    <span class="workflow-text">{{ step.step }}</span>
                    <span v-if="step.detail" class="workflow-detail">{{ step.detail }}</span>
                  </div>
                </div>
                <div v-if="msg.role === 'assistant'" class="bubble markdown-body" v-html="renderContent(msg)" />
                <div v-else class="bubble">{{ msg.content }}</div>
                <div v-if="msg.role === 'assistant' && (msg.content || '').trim()" class="msg-actions">
                  <el-button text size="small" @click="copyContent(msg.content)">
                    <el-icon><CopyDocument /></el-icon>
                    复制
                  </el-button>
                  <el-button text size="small" @click="insertAssistantMessage(msg.content)">
                    <el-icon><Download /></el-icon>
                    插入到文稿
                  </el-button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div class="input-area" v-if="currentSession">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="4"
            placeholder="输入写作诉求或修改意见... (Ctrl+Enter 发送)"
            @keyup.ctrl.enter="sendMessage"
            resize="none"
          />
          <div class="actions">
            <el-button type="primary" @click="sendMessage" :loading="sending" :disabled="sending || !inputText.trim()">
              发送
            </el-button>
            <el-button v-if="sending" type="danger" plain @click="stopGenerating">
              停止生成
            </el-button>
            <el-button @click="exportDoc" :disabled="sending || !currentSession">
              导出 docx
            </el-button>
          </div>
        </div>
      </section>

      <section class="editor-panel" :class="{ hidden: isMobile && mobileTab !== 'editor' }">
        <div class="editor-header">
          <h3>公文编辑器</h3>
          <span v-if="currentSession" class="session-hint">会话草稿独立保存</span>
        </div>

        <template v-if="!currentSession">
          <div class="empty-chat">
            <el-icon :size="48" color="#c0c4cc"><Document /></el-icon>
            <p>选择会话后开始编辑文稿</p>
          </div>
        </template>
        <template v-else-if="loadingDraft">
          <el-skeleton :rows="8" animated style="padding: 12px" />
        </template>
        <OfficialDocEditor
          v-else
          ref="editorRef"
          v-model="draft"
          :save-status="saveStatusText"
          :saving="saveState === 'saving-auto' || saveState === 'saving-manual'"
          :last-saved-at="lastSavedAt"
          @manual-save="manualSave"
          @quote-selection="appendSelectionToInput"
        />
      </section>
    </main>

    <el-dialog v-model="showNewSession" title="新建写作会话" width="420px" :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="例如：关于开展交通整治的通知" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="公文类型">
          <el-select v-model="newDocType" placeholder="请选择公文类型" style="width: 100%">
            <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewSession = false">取消</el-button>
        <el-button type="primary" @click="createSession" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Close,
  CopyDocument,
  Document,
  Download,
  Edit,
  EditPen,
  Menu,
  Monitor,
  Plus,
  User,
} from '@element-plus/icons-vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import api from '@/api'
import apiChat from '@/api/modules/chat'
import apiDocuments from '@/api/modules/documents'
import { useUserStore } from '@/store/modules/user'
import type { ChatMessage, ChatSession, ChatWorkflowStep, WriterDraft } from '@/types/writer'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import { DOC_TYPES } from '@/utils/constants'
import OfficialDocEditor from './components/OfficialDocEditor.vue'

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
  } else {
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
  } catch {
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
  } catch {
    sessions.value = []
  } finally {
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
    ElMessage.warning('上一个会话草稿保存失败，已保留本地未保存状态')
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
  } catch {
    messages.value = []
    hydratingDraft.value = true
    draft.value = createEmptyDraft(session.title)
    await nextTick()
    hydratingDraft.value = false

    draftDirty.value = false
    saveState.value = 'idle'
    lastSavedAt.value = ''
  } finally {
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
  } catch {
    ElMessage.error('创建失败，请稍后重试')
  } finally {
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
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      const idx = messages.value.findIndex(m => m.id === assistantTempId)
      if (idx !== -1 && !assistantMsg.content.trim() && !(assistantMsg.workflow_steps?.length)) {
        messages.value.splice(idx, 1)
      }
      ElMessage.info('已停止生成')
    } else {
      messages.value = messages.value.filter(m => m.id !== userTempId && m.id !== assistantTempId)
      inputText.value = text
      ElMessage.error(error?.message || '发送失败，请稍后重试')
    }
  } finally {
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
    a.download = `${draft.value.title || currentSession.value.title || '公文'}.docx`
    a.click()
    URL.revokeObjectURL(blobUrl)

    ElMessage.success('导出成功')
  } catch {
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
  } catch {
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
  } catch {
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
  } catch (error: any) {
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

<style scoped>
.writing-chat {
  --wc-black: var(--w-color-black);
  --wc-white: var(--w-color-white);
  --wc-gray-900: var(--w-gray-900);
  --wc-gray-800: var(--w-gray-800);
  --wc-gray-700: var(--w-gray-700);
  --wc-gray-600: var(--w-gray-600);
  --wc-gray-500: var(--w-gray-500);
  --wc-gray-400: var(--w-gray-400);
  --wc-gray-300: var(--w-gray-300);
  --wc-gray-200: var(--w-gray-200);
  --wc-gray-100: var(--w-gray-100);
  --wc-gray-50: var(--w-gray-50);
  --el-color-primary: var(--wc-black);
  --el-color-primary-light-3: #3f3f3f;
  --el-color-primary-light-5: #666666;
  --el-color-primary-light-7: #949494;
  --el-color-primary-light-8: #b8b8b8;
  --el-color-primary-light-9: #ececec;
  --el-color-primary-dark-2: #000000;
  --el-color-success: var(--wc-black);
  --el-color-warning: var(--wc-gray-700);
  --el-color-danger: var(--wc-black);
  --el-color-info: var(--wc-gray-600);
  --el-text-color-primary: var(--wc-black);
  --el-text-color-secondary: var(--wc-gray-600);
  --el-border-color: var(--wc-gray-300);
  --el-border-color-light: var(--wc-gray-200);
  --el-border-color-lighter: var(--wc-gray-200);
  --el-fill-color-light: var(--wc-gray-100);
  --el-fill-color-lighter: var(--wc-gray-50);
  display: flex;
  height: calc(100vh - var(--g-header-height));
  position: relative;
  background: linear-gradient(180deg, var(--wc-white) 0%, var(--wc-gray-50) 100%);
  color: var(--wc-gray-900);
}

.writing-chat :deep(.el-input__wrapper),
.writing-chat :deep(.el-select__wrapper),
.writing-chat :deep(.el-textarea__inner) {
  border-radius: var(--w-radius-lg);
}

.sidebar {
  width: 280px;
  padding: 14px;
  overflow-y: auto;
  background: var(--wc-white);
  border-right: 1px solid var(--wc-gray-200);
  box-shadow: 6px 0 20px rgb(0 0 0 / 3%);
}

.new-btn {
  width: 100%;
  height: 40px;
  border-radius: var(--w-radius-md);
  box-shadow: var(--w-shadow-sm);
}

.session-search {
  margin-top: 10px;
}

.session-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 1px solid var(--wc-gray-200);
  text-align: left;
  padding: 10px 12px;
  border-radius: var(--w-radius-lg);
  background: var(--wc-white);
  cursor: pointer;
  transition: all 0.18s ease;
}

.session-item:hover {
  background: var(--wc-gray-100);
  border-color: var(--wc-black);
  box-shadow: var(--w-shadow-sm);
}

.session-item.active {
  background: var(--wc-white);
  border-color: var(--wc-black);
  box-shadow: var(--w-shadow-md);
}

.session-item.active .session-title,
.session-item.active .session-time {
  color: var(--wc-black);
}

.session-item.active .session-tag {
  color: var(--wc-black);
  border-color: var(--wc-black);
  background: var(--wc-white);
}

.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-title {
  font-size: 14px;
  color: var(--wc-black);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 12px;
  color: var(--wc-gray-600);
}

.session-tag {
  align-self: flex-start;
}

.session-actions {
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.edit-btn,
.delete-btn {
  color: var(--wc-gray-500);
  padding: 2px;
  border-radius: var(--w-radius-sm);
  cursor: pointer;
  transition: all 0.18s ease;
}

.edit-btn:hover {
  color: var(--wc-black);
  background: var(--wc-gray-100);
}

.delete-btn:hover {
  color: var(--wc-black);
  background: var(--wc-gray-100);
}

.session-item.active .edit-btn,
.session-item.active .delete-btn {
  color: var(--wc-gray-500);
}

.session-item.active .edit-btn:hover,
.session-item.active .delete-btn:hover {
  color: var(--wc-black);
  background: var(--wc-gray-100);
}

.workspace {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(420px, 1fr);
}

.mobile-tab-toggle {
  display: none;
}

.chat-panel,
.editor-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-panel {
  background: var(--wc-white);
}

.editor-panel {
  background: var(--wc-white);
  border-left: 1px solid var(--wc-gray-200);
}

.chat-header,
.editor-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--wc-gray-200);
  background: rgb(255 255 255 / 94%);
  backdrop-filter: blur(3px);
}

.editor-header {
  justify-content: space-between;
}

.chat-header h3,
.editor-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--wc-black);
}

.session-hint {
  font-size: 12px;
  color: var(--wc-gray-600);
}

.session-toggle-btn {
  display: none;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar.assistant {
  color: var(--wc-white);
  background: var(--wc-black);
  box-shadow: 0 5px 12px rgb(0 0 0 / 16%);
}

.avatar.user {
  color: var(--wc-black);
  border: 1px solid var(--wc-black);
  background: var(--wc-white);
  box-shadow: 0 3px 8px rgb(0 0 0 / 10%);
}

.bubble-wrap {
  max-width: 78%;
  min-width: 80px;
}

.workflow-card {
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid var(--wc-gray-200);
  border-radius: var(--w-radius-md);
  background: var(--wc-gray-50);
}

.workflow-title {
  font-size: 12px;
  color: var(--wc-gray-600);
  margin-bottom: 6px;
}

.workflow-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--wc-gray-900);
  line-height: 1.6;
}

.workflow-item + .workflow-item {
  margin-top: 2px;
}

.workflow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: 1px solid transparent;
  background: var(--wc-gray-400);
  flex: 0 0 auto;
}

.workflow-item.is-running .workflow-dot {
  background: var(--wc-gray-600);
}

.workflow-item.is-done .workflow-dot {
  background: var(--wc-black);
}

.workflow-item.is-error .workflow-dot {
  border-color: var(--wc-black);
  background: var(--wc-white);
}

.workflow-text {
  flex: 0 1 auto;
}

.workflow-detail {
  color: var(--wc-gray-600);
  font-size: 12px;
}

.bubble {
  padding: 12px 16px;
  border-radius: var(--w-radius-lg);
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
  box-shadow: 0 6px 14px rgb(0 0 0 / 4%);
}

.message.user .bubble {
  color: var(--wc-white);
  border-top-right-radius: var(--w-radius-sm);
  border: 1px solid var(--wc-black);
  background: var(--wc-black);
  white-space: pre-wrap;
}

.message.assistant .bubble {
  color: var(--wc-black);
  border-top-left-radius: var(--w-radius-sm);
  border: 1px solid var(--wc-gray-200);
  background: var(--wc-white);
}

.message.sending {
  opacity: 0.65;
}

.msg-actions {
  margin-top: 4px;
  display: flex;
  gap: 2px;
}

.msg-actions .el-button {
  font-size: 12px;
  color: var(--wc-gray-600);
  border-radius: var(--w-radius-sm);
}

.msg-actions .el-button:hover {
  color: var(--wc-black);
  background: var(--wc-gray-100);
}

.input-area {
  padding: 14px 18px;
  border-top: 1px solid var(--wc-gray-200);
  background: var(--wc-white);
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.empty-tip {
  padding: 20px 8px;
  text-align: center;
  color: var(--wc-gray-600);
  font-size: 13px;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--wc-gray-600);
  gap: 12px;
}

.empty-chat p {
  margin: 0;
  font-size: 14px;
}

.mobile-session-trigger,
.sidebar-mask {
  display: none;
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.markdown-body :deep(code) {
  color: var(--wc-black);
  background: var(--wc-gray-100);
  padding: 2px 6px;
  border-radius: var(--w-radius-sm);
  font-size: 13px;
}

.markdown-body :deep(pre) {
  color: var(--wc-white);
  background: var(--wc-black);
  padding: 14px;
  border-radius: var(--w-radius-md);
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--wc-black);
  padding: 8px 12px;
  color: var(--wc-gray-800);
  margin: 8px 0;
  background: var(--wc-gray-100);
  border-radius: 0 var(--w-radius-sm) var(--w-radius-sm) 0;
}

@media (hover: none) {
  .session-actions {
    opacity: 1;
  }
}

@media (max-width: 900px) {
  .writing-chat {
    display: block;
  }

  .sidebar {
    position: absolute;
    z-index: 30;
    inset: 0 auto 0 0;
    width: min(84vw, 320px);
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: var(--w-shadow-md);
  }

  .sidebar.is-mobile-open {
    transform: translateX(0);
  }

  .sidebar-mask {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 20;
    background: rgb(0 0 0 / 38%);
  }

  .mobile-session-trigger {
    display: inline-flex;
    position: absolute;
    z-index: 10;
    right: 16px;
    bottom: 16px;
  }

  .workspace {
    display: block;
    height: 100%;
  }

  .mobile-tab-toggle {
    display: flex;
    justify-content: center;
    padding: 10px 12px 0;
  }

  .chat-panel,
  .editor-panel {
    height: calc(100vh - var(--g-header-height) - 56px);
  }

  .chat-panel.hidden,
  .editor-panel.hidden {
    display: none;
  }

  .session-toggle-btn {
    display: inline-flex;
  }

  .chat-header,
  .editor-header {
    padding-inline: 12px;
  }

  .messages {
    padding: 12px;
  }

  .bubble-wrap {
    max-width: 90%;
  }

  .input-area {
    padding: 12px;
  }
}
</style>

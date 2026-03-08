import type { ChatMessage, ChatSession, WriterDraft } from '@/types/writer'
import DOMPurify from 'dompurify'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import api from '@/api'
import apiChat from '@/api/modules/chat'
import apiDocuments from '@/api/modules/documents'
import dayjs, { SHANGHAI_TZ } from '@/utils/dayjs'
import { useWritingSessions } from './useWritingSessions'

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

export function useWritingWorkspace() {
  const userStore = useUserStore()
  const { ensureSessionById, findSessionById, rememberLastSession } = useWritingSessions()
  const md = new MarkdownIt({ breaks: true, linkify: true })

  const activeSessionId = ref<number | null>(null)
  const sessionSnapshot = ref<ChatSession | null>(null)
  const currentSession = computed(() => {
    if (!activeSessionId.value) {
      return null
    }
    return findSessionById(activeSessionId.value) || sessionSnapshot.value
  })

  const messages = ref<ChatMessage[]>([])
  const draft = ref<WriterDraft>(createEmptyDraft())
  const inputText = ref('')
  const sending = ref(false)
  const loadingMessages = ref(false)
  const loadingDraft = ref(false)
  const mobileTab = ref<'chat' | 'editor'>('chat')
  const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth <= 900 : false)
  const saveState = ref<SaveState>('idle')
  const draftDirty = ref(false)
  const lastSavedAt = ref('')
  const hydratingDraft = ref(false)
  const messagesRef = ref<HTMLElement>()
  const editorRef = ref<OfficialEditorExpose | null>(null)

  const abortController = ref<AbortController | null>(null)
  const skipNextLeaveFlush = ref(false)
  let msgIdCounter = 0
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

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

  function renderContent(message: ChatMessage) {
    if (message.role !== 'assistant') {
      return ''
    }
    return DOMPurify.sanitize(md.render(message.content || ''))
  }

  function normalizeWorkflowStatus(status?: string): 'running' | 'done' | 'error' {
    if (status === 'done' || status === 'error') {
      return status
    }
    return 'running'
  }

  function upsertWorkflowStep(message: ChatMessage, payload: WorkflowEventPayload) {
    if (!payload.step) {
      return
    }
    const status = normalizeWorkflowStatus(payload.status)
    const steps = message.workflow_steps ? [...message.workflow_steps] : []
    const key = payload.step.trim()
    const index = steps.findIndex(item => item.step === key)
    if (index === -1) {
      steps.push({
        id: `wf-${Date.now()}-${msgIdCounter++}`,
        step: key,
        status,
        detail: payload.detail,
      })
    }
    else {
      steps[index] = {
        ...steps[index],
        status,
        detail: payload.detail || steps[index].detail,
      }
    }
    message.workflow_steps = steps
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

  async function flushDraftBeforeLeave() {
    if (!currentSession.value || !draftDirty.value) {
      return true
    }
    return persistDraft('auto', { timeout: 2500, silent: true, force: true })
  }

  async function prepareRouteChange(options: { warnOnFailure?: boolean } = {}) {
    const saved = await flushDraftBeforeLeave()
    if (!saved && options.warnOnFailure) {
      ElMessage.warning('当前会话草稿保存失败，已保留本地未保存状态')
    }
    skipNextLeaveFlush.value = true
    return saved
  }

  function skipNextRouteLeaveFlush() {
    skipNextLeaveFlush.value = true
  }

  function resetWorkspace() {
    activeSessionId.value = null
    sessionSnapshot.value = null
    messages.value = []
    draft.value = createEmptyDraft()
    inputText.value = ''
    saveState.value = 'idle'
    draftDirty.value = false
    lastSavedAt.value = ''
    mobileTab.value = 'chat'
    clearAutoSaveTimer()
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

  async function loadSessionState(session: ChatSession) {
    activeSessionId.value = Number(session.id)
    sessionSnapshot.value = session
    rememberLastSession(session.id)
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
      return true
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
      return true
    }
    finally {
      loadingMessages.value = false
      loadingDraft.value = false
    }
  }

  async function openSessionById(value: number | string | null | undefined) {
    const session = await ensureSessionById(value)
    if (!session) {
      resetWorkspace()
      return false
    }
    return loadSessionState(session)
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
    const assistantMessage: ChatMessage = { id: assistantTempId, role: 'assistant', content: '', workflow_steps: [] }
    messages.value.push(assistantMessage)
    scrollToBottom()

    try {
      const response = await fetch(getStreamUrl(), {
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

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
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
          upsertWorkflowStep(assistantMessage, parsed as WorkflowEventPayload)
          const index = messages.value.findIndex(message => message.id === assistantTempId)
          if (index !== -1) {
            messages.value[index] = { ...assistantMessage }
          }
          scrollToBottom()
          return
        }
        if (parsed.chunk) {
          assistantMessage.content += parsed.chunk
          const index = messages.value.findIndex(message => message.id === assistantTempId)
          if (index !== -1) {
            messages.value[index] = { ...assistantMessage }
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
      if (assistantMessage.content.trim() || assistantMessage.workflow_steps?.length) {
        const index = messages.value.findIndex(message => message.id === assistantTempId)
        if (index !== -1) {
          messages.value[index] = {
            ...assistantMessage,
            id: `assistant-${Date.now()}-${msgIdCounter++}`,
          }
        }
      }
    }
    catch (error: any) {
      if (error?.name === 'AbortError') {
        const index = messages.value.findIndex(message => message.id === assistantTempId)
        if (index !== -1 && !assistantMessage.content.trim() && !(assistantMessage.workflow_steps?.length)) {
          messages.value.splice(index, 1)
        }
        ElMessage.info('已停止生成')
      }
      else {
        messages.value = messages.value.filter(message => message.id !== userTempId && message.id !== assistantTempId)
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
    if (!text) {
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
    const payload = `【引用文稿片段】
${selectedText}

请基于以上片段继续修改：`
    inputText.value = inputText.value.trim()
      ? `${inputText.value.trim()}

${payload}`
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
      const response = await apiDocuments.exportEditorDoc({
        session_id: currentSession.value.id,
        doc_type: currentSession.value.doc_type || '',
        draft: draft.value,
      })

      const blobUrl = URL.createObjectURL(response.data)
      const anchor = window.document.createElement('a')
      anchor.href = blobUrl
      const exportTitle = extractH1TitleFromBody(draft.value.body_json) || draft.value.title || '文稿'
      anchor.download = `${exportTitle}.docx`
      anchor.click()
      URL.revokeObjectURL(blobUrl)

      ElMessage.success('导出成功')
    }
    catch {
      ElMessage.error('导出失败，请稍后重试')
    }
  }

  function handleResize() {
    const mobile = window.innerWidth <= 900
    isMobile.value = mobile
    if (!mobile) {
      mobileTab.value = 'chat'
    }
  }

  onMounted(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', handleResize)
    }
  })

  onBeforeUnmount(() => {
    abortController.value?.abort()
    clearAutoSaveTimer()
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', handleResize)
    }
  })

  return {
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
    persistDraft,
    prepareRouteChange,
    renderContent,
    resetWorkspace,
    saveState,
    saveStatusText,
    scrollToBottom,
    sendMessage,
    sending,
    skipNextLeaveFlush,
    skipNextRouteLeaveFlush,
    stopGenerating,
  }
}

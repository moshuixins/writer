<template>
  <div class="writing-chat">
    <div class="sidebar">
      <el-button type="primary" @click="showNewSession = true" class="new-btn">
        <el-icon style="margin-right:6px"><Plus /></el-icon>新建写作
      </el-button>
      <div class="session-list">
        <template v-if="loadingSessions">
          <el-skeleton :rows="3" animated style="padding: 8px" />
        </template>
        <template v-else-if="sessions.length === 0">
          <div class="empty-tip">暂无会话，点击上方新建</div>
        </template>
        <div
          v-else
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: currentSession?.id === s.id }"
          @click="selectSession(s)"
        >
          <div class="session-info">
            <span class="session-title">{{ s.title }}</span>
            <el-tag v-if="s.doc_type" size="small" type="info" class="session-tag">{{ s.doc_type }}</el-tag>
          </div>
          <el-icon class="delete-btn" @click.stop="deleteSession(s.id)"><Close /></el-icon>
        </div>
      </div>
    </div>

    <div class="chat-area">
      <div class="chat-header" v-if="currentSession">
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
            <p>请从左侧选择或新建一个写作会话</p>
          </div>
        </template>
        <template v-else-if="messages.length === 0">
          <div class="empty-chat">
            <el-icon :size="48" color="#c0c4cc"><EditPen /></el-icon>
            <p>发送你的写作需求，开始创作</p>
          </div>
        </template>
        <template v-else>
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message"
            :class="[msg.role, { sending: msg.id?.toString().startsWith('sending-') }]"
          >
            <div class="avatar" :class="msg.role">
              <el-icon v-if="msg.role === 'assistant'" :size="18"><Monitor /></el-icon>
              <el-icon v-else :size="18"><User /></el-icon>
            </div>
            <div class="bubble-wrap">
              <div v-if="msg.role === 'assistant'" class="bubble markdown-body" v-html="renderContent(msg)"></div>
              <div v-else class="bubble">{{ msg.content }}</div>
              <div v-if="msg.role === 'assistant' && !msg.id?.toString().startsWith('sending-')" class="msg-actions">
                <el-button text size="small" @click="copyContent(msg.content)">
                  <el-icon><CopyDocument /></el-icon> 复制
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
          :rows="3"
          placeholder="输入写作需求或修改意见... (Ctrl+Enter 发送)"
          @keyup.ctrl.enter="sendMessage"
          resize="none"
        />
        <div class="actions">
          <el-button type="primary" @click="sendMessage" :loading="sending" :disabled="!inputText.trim()">
            发送
          </el-button>
          <el-button @click="exportDoc" :disabled="!lastContent">导出 docx</el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="showNewSession" title="新建写作" width="420px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="如：关于开展交通安全整治的通知" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="公文类型">
          <el-select v-model="newDocType" placeholder="选择公文类型" style="width: 100%">
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
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, Plus, Monitor, User, CopyDocument, ChatDotRound, EditPen } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import api from '../api'
import { DOC_TYPES } from '../types'
import type { ChatSession, ChatMessage } from '../types'

const md = new MarkdownIt({ breaks: true, linkify: true })

function renderContent(msg: ChatMessage): string {
  if (msg.role === 'assistant') {
    return DOMPurify.sanitize(md.render(msg.content || ''))
  }
  return ''
}

function copyContent(text: string) {
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.warning('复制失败，请手动选择复制'),
  )
}

let msgIdCounter = 0

const sessions = ref<ChatSession[]>([])
const currentSession = ref<ChatSession | null>(null)
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const sending = ref(false)
const showNewSession = ref(false)
const newTitle = ref('')
const newDocType = ref('')
const creating = ref(false)
const lastContent = ref('')
const messagesRef = ref<HTMLElement>()
const loadingSessions = ref(false)
const loadingMessages = ref(false)

async function createSession() {
  if (!newTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  creating.value = true
  try {
    const { data } = await api.post('/chat/sessions', {
      title: newTitle.value,
      doc_type: newDocType.value || null,
    })
    sessions.value.unshift(data)
    currentSession.value = data
    messages.value = []
    lastContent.value = ''
    showNewSession.value = false
    newTitle.value = ''
    newDocType.value = ''
  } catch {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function loadSessions() {
  loadingSessions.value = true
  try {
    const { data } = await api.get('/chat/sessions')
    sessions.value = data
  } catch {
    sessions.value = []
  } finally {
    loadingSessions.value = false
  }
}

async function selectSession(s: ChatSession) {
  currentSession.value = s
  loadingMessages.value = true
  try {
    const { data } = await api.get(`/chat/sessions/${s.id}/messages`)
    messages.value = data
    scrollToBottom()
  } catch {
    messages.value = []
  } finally {
    loadingMessages.value = false
  }
}

async function sendMessage() {
  if (!inputText.value.trim() || !currentSession.value) return
  sending.value = true
  const text = inputText.value
  inputText.value = ''

  const tempId = `sending-${msgIdCounter++}`
  messages.value.push({ id: tempId, role: 'user', content: text })
  scrollToBottom()

  // 创建一条空的 assistant 消息，用于逐字填充
  const assistantId = `stream-${msgIdCounter++}`
  const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '' }
  messages.value.push(assistantMsg)
  scrollToBottom()

  try {
    const token = localStorage.getItem('token')
    const resp = await fetch('/api/chat/send-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        session_id: currentSession.value.id,
        message: text,
      }),
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 保留最后一行（可能不完整）
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (payload === '[DONE]') continue
        try {
          const parsed = JSON.parse(payload)
          if (parsed.error) {
            ElMessage.error(parsed.error)
            break
          }
          if (parsed.chunk) {
            assistantMsg.content += parsed.chunk
            // 直接修改响应式数组中的对象，Vue 会追踪
            const idx = messages.value.findIndex(m => m.id === assistantId)
            if (idx !== -1) {
              messages.value[idx] = { ...assistantMsg }
            }
            scrollToBottom()
          }
        } catch {
          // 忽略解析失败的行
        }
      }
    }

    lastContent.value = assistantMsg.content
  } catch {
    // 发送失败，回滚用户消息和空的 assistant 消息，恢复输入
    messages.value = messages.value.filter(m => m.id !== tempId && m.id !== assistantId)
    inputText.value = text
    ElMessage.error('发送失败，请重试')
  } finally {
    sending.value = false
  }
}

async function exportDoc() {
  if (!lastContent.value) return

  let contentJson: Record<string, unknown>
  try {
    contentJson = JSON.parse(lastContent.value)
    if (typeof contentJson !== 'object' || contentJson === null) {
      throw new Error('not object')
    }
  } catch {
    ElMessage.warning('内容格式不支持直接导出，请先让AI生成结构化内容')
    return
  }

  try {
    const resp = await api.post('/documents/export', {
      content_json: contentJson,
      title: currentSession.value?.title || '公文',
      doc_type: currentSession.value?.doc_type || '',
      session_id: currentSession.value?.id,
    }, { responseType: 'blob' })

    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentSession.value?.title || '公文'}.docx`
    a.click()
    URL.revokeObjectURL(url)
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
    await api.delete(`/chat/sessions/${id}`)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSession.value?.id === id) {
      currentSession.value = null
      messages.value = []
      lastContent.value = ''
    }
    ElMessage.success('会话已删除')
  } catch {
    // interceptor handles error display
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

onMounted(loadSessions)
</script>

<style scoped>
.writing-chat { display: flex; height: 100vh; }

/* 侧边栏 */
.sidebar {
  width: 260px; border-right: 1px solid #ebeef5; padding: 16px;
  overflow-y: auto; background: #fafbfc;
}
.new-btn { width: 100%; border-radius: 8px; }
.session-list { margin-top: 16px; }
.session-item {
  padding: 10px 32px 10px 12px; cursor: pointer; border-radius: 8px;
  margin-bottom: 4px; position: relative; transition: background 0.2s;
}
.session-item:hover { background: #ecf5ff; }
.session-item.active { background: #d9ecff; }
.session-info { display: flex; flex-direction: column; gap: 4px; }
.session-title { font-size: 14px; color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-tag { align-self: flex-start; }
.delete-btn {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  color: #c0c4cc; cursor: pointer; font-size: 14px; opacity: 0; transition: opacity 0.2s;
}
.session-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: #f56c6c; }
</style>

<style scoped>
/* 聊天区域 */
.chat-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-header {
  padding: 12px 20px; border-bottom: 1px solid #ebeef5;
  display: flex; align-items: center; gap: 10px; background: #fff;
}
.chat-header h3 { margin: 0; font-size: 16px; color: #303133; }
.messages { flex: 1; overflow-y: auto; padding: 20px; background: #f5f7fa; }
</style>

<style scoped>
/* 消息气泡 */
.message { display: flex; gap: 10px; margin-bottom: 20px; }
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.avatar.assistant { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; }
.avatar.user { background: linear-gradient(135deg, #409eff, #53a8ff); color: #fff; }
.bubble-wrap { max-width: 75%; min-width: 60px; }
.bubble {
  padding: 12px 16px; border-radius: 12px; line-height: 1.7;
  font-size: 14px; word-break: break-word;
}
.message.user .bubble {
  background: #409eff; color: #fff; border-top-right-radius: 4px; white-space: pre-wrap;
}
.message.assistant .bubble {
  background: #fff; border: 1px solid #ebeef5; border-top-left-radius: 4px; color: #303133;
}
.message.sending { opacity: 0.6; }
.msg-actions { margin-top: 4px; }
.msg-actions .el-button { color: #909399; font-size: 12px; }
.msg-actions .el-button:hover { color: #409eff; }
</style>

<style scoped>
/* 输入区域 */
.input-area { padding: 16px 20px; border-top: 1px solid #ebeef5; background: #fff; }
.actions { margin-top: 10px; display: flex; gap: 8px; }

/* 空状态 */
.empty-tip { padding: 20px 8px; text-align: center; color: #909399; font-size: 13px; }
.empty-chat {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; color: #909399; gap: 12px;
}
.empty-chat p { margin: 0; font-size: 15px; }
</style>

<style scoped>
/* Markdown 样式 */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin: 4px 0; }
.markdown-body :deep(code) { background: #f0f2f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #c7254e; }
.markdown-body :deep(pre) { background: #1e1e2e; color: #cdd6f4; padding: 14px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
.markdown-body :deep(pre code) { background: none; padding: 0; color: inherit; }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) { margin: 12px 0 6px; }
.markdown-body :deep(blockquote) { border-left: 3px solid #409eff; padding-left: 12px; color: #606266; margin: 8px 0; background: #f4f7fe; border-radius: 0 4px 4px 0; padding: 8px 12px; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid #ebeef5; padding: 8px 12px; text-align: left; }
.markdown-body :deep(th) { background: #f5f7fa; font-weight: 600; }
</style>

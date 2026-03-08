import type {
  ChatChunkSseEventResponse,
  ChatFinalSseEventResponse,
  ChatStreamEventResponse,
  ChatWorkflowSseEventResponse,
} from '../generated'
import { resolveApiUrl } from '@/api'

export type ChatStreamWorkflowEvent = ChatWorkflowSseEventResponse
export type ChatStreamFinalEvent = ChatFinalSseEventResponse

interface StreamChatRequest {
  session_id: number
  message: string
}

interface StreamChatOptions {
  signal?: AbortSignal
  token?: string
  onWorkflow?: (event: ChatWorkflowSseEventResponse) => void
  onChunk?: (chunk: string, event: ChatChunkSseEventResponse) => void
  onFinal?: (event: ChatFinalSseEventResponse) => void
  onDone?: () => void
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isWorkflowStatus(value: unknown): value is ChatWorkflowSseEventResponse['status'] {
  return value === 'running' || value === 'done' || value === 'error'
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string')
}

function normalizeLegacyPayload(parsed: unknown): ChatStreamEventResponse | null {
  if (!isRecord(parsed)) {
    return null
  }
  if (typeof parsed.chunk === 'string') {
    return { event: 'chunk', chunk: parsed.chunk }
  }
  if (typeof parsed.error === 'string') {
    return { event: 'error', error: parsed.error }
  }
  return null
}

function parseChatStreamEvent(payloadText: string): ChatStreamEventResponse {
  const parsed: unknown = JSON.parse(payloadText)
  const legacyEvent = normalizeLegacyPayload(parsed)
  if (legacyEvent) {
    return legacyEvent
  }
  if (!isRecord(parsed) || typeof parsed.event !== 'string') {
    throw new Error('无效流事件')
  }

  switch (parsed.event) {
    case 'workflow':
      if (typeof parsed.step === 'string' && isWorkflowStatus(parsed.status)) {
        return {
          event: 'workflow',
          step: parsed.step,
          status: parsed.status,
          detail: typeof parsed.detail === 'string' ? parsed.detail : undefined,
        }
      }
      break
    case 'chunk':
      if (typeof parsed.chunk === 'string') {
        return { event: 'chunk', chunk: parsed.chunk }
      }
      break
    case 'error':
      if (typeof parsed.error === 'string') {
        return { event: 'error', error: parsed.error }
      }
      break
    case 'final':
      if (
        isRecord(parsed.message)
        && (typeof parsed.message.id === 'number' || typeof parsed.message.id === 'string')
        && typeof parsed.message.role === 'string'
        && typeof parsed.message.content === 'string'
      ) {
        return {
          event: 'final',
          message: {
            id: parsed.message.id,
            role: parsed.message.role,
            content: parsed.message.content,
            created_at: typeof parsed.message.created_at === 'string' ? parsed.message.created_at : undefined,
          },
          warnings: isStringArray(parsed.warnings) ? parsed.warnings : undefined,
        }
      }
      break
  }

  throw new Error('无效流事件')
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const contentType = String(response.headers.get('content-type') || '')
    if (contentType.includes('application/json')) {
      const payload = await response.json()
      return payload?.error || payload?.detail || `HTTP ${response.status}`
    }

    const text = (await response.text()).trim()
    return text || `HTTP ${response.status}`
  }
  catch {
    return `HTTP ${response.status}`
  }
}

export async function streamChatReply(
  payload: StreamChatRequest,
  options: StreamChatOptions = {},
) {
  const response = await fetch(resolveApiUrl('/api/chat/send-stream'), {
    method: 'POST',
    signal: options.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('读取响应流失败')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let doneEventSeen = false

  const processLine = (line: string) => {
    if (!line.startsWith('data:')) {
      return
    }

    const payloadText = line.replace(/^data:\s?/, '').trim()
    if (!payloadText) {
      return
    }
    if (payloadText === '[DONE]') {
      if (!doneEventSeen) {
        doneEventSeen = true
        options.onDone?.()
      }
      return
    }

    const event = parseChatStreamEvent(payloadText)
    switch (event.event) {
      case 'workflow':
        options.onWorkflow?.(event)
        return
      case 'chunk':
        options.onChunk?.(event.chunk, event)
        return
      case 'final':
        options.onFinal?.(event)
        return
      case 'error':
        throw new Error(event.error)
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
      processLine(line.trim())
    }
  }

  const trailing = buffer.trim()
  if (trailing) {
    processLine(trailing)
  }
}

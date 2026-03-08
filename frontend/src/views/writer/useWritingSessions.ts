import type { ChatSession } from '@/types/writer'
import apiChat from '@/api/modules/chat'

const SESSION_KEYWORD_STORAGE_KEY = 'writer:session-keyword'
const LAST_SESSION_STORAGE_KEY = 'writer:last-session-id'

const sessions = ref<ChatSession[]>([])
const loadingSessions = ref(false)
const sessionsLoaded = ref(false)
const sessionKeyword = ref(readStoredKeyword())
const lastOpenedSessionId = ref<number | null>(readStoredSessionId())

const filteredSessions = computed(() => {
  const keyword = sessionKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return sessions.value
  }
  return sessions.value.filter(session => (session.title || '').toLowerCase().includes(keyword))
})

const lastOpenedSession = computed(() => {
  if (!lastOpenedSessionId.value) {
    return null
  }
  return sessions.value.find(session => Number(session.id) === lastOpenedSessionId.value) || null
})

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
}

function readStoredKeyword() {
  if (!canUseStorage()) {
    return ''
  }
  return window.sessionStorage.getItem(SESSION_KEYWORD_STORAGE_KEY) || ''
}

function readStoredSessionId() {
  if (!canUseStorage()) {
    return null
  }
  const raw = window.sessionStorage.getItem(LAST_SESSION_STORAGE_KEY)
  if (!raw) {
    return null
  }
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function writeStoredKeyword(value: string) {
  if (!canUseStorage()) {
    return
  }
  if (value.trim()) {
    window.sessionStorage.setItem(SESSION_KEYWORD_STORAGE_KEY, value)
  }
  else {
    window.sessionStorage.removeItem(SESSION_KEYWORD_STORAGE_KEY)
  }
}

function writeStoredSessionId(value: number | null) {
  if (!canUseStorage()) {
    return
  }
  if (value) {
    window.sessionStorage.setItem(LAST_SESSION_STORAGE_KEY, String(value))
  }
  else {
    window.sessionStorage.removeItem(LAST_SESSION_STORAGE_KEY)
  }
}

function normalizeSessionId(value: number | string | null | undefined) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function syncLastSessionPointer() {
  if (!lastOpenedSessionId.value) {
    return
  }
  const exists = sessions.value.some(session => Number(session.id) === lastOpenedSessionId.value)
  if (!exists) {
    lastOpenedSessionId.value = null
    writeStoredSessionId(null)
  }
}

function setKeyword(value: string) {
  sessionKeyword.value = value
  writeStoredKeyword(value)
}

function rememberLastSession(value: number | string | null | undefined) {
  lastOpenedSessionId.value = normalizeSessionId(value)
  writeStoredSessionId(lastOpenedSessionId.value)
}

function upsertSession(session: ChatSession, options: { moveToFront?: boolean } = {}) {
  const index = sessions.value.findIndex(item => Number(item.id) === Number(session.id))
  if (index === -1) {
    sessions.value = [session, ...sessions.value]
    return session
  }

  const nextSession = { ...sessions.value[index], ...session }
  const nextSessions = [...sessions.value]
  nextSessions.splice(index, 1)
  if (options.moveToFront) {
    nextSessions.unshift(nextSession)
  }
  else {
    nextSessions.splice(index, 0, nextSession)
  }
  sessions.value = nextSessions
  return nextSession
}

async function loadSessions(options: { force?: boolean } = {}) {
  if (loadingSessions.value) {
    return sessions.value
  }
  if (!options.force && sessionsLoaded.value) {
    return sessions.value
  }

  loadingSessions.value = true
  try {
    const { data } = await apiChat.getSessions()
    sessions.value = data
    sessionsLoaded.value = true
    syncLastSessionPointer()
    return sessions.value
  }
  catch {
    sessions.value = []
    sessionsLoaded.value = false
    throw new Error('加载会话失败')
  }
  finally {
    loadingSessions.value = false
  }
}

function findSessionById(value: number | string | null | undefined) {
  const sessionId = normalizeSessionId(value)
  if (!sessionId) {
    return null
  }
  return sessions.value.find(session => Number(session.id) === sessionId) || null
}

async function ensureSessionById(value: number | string | null | undefined) {
  const sessionId = normalizeSessionId(value)
  if (!sessionId) {
    return null
  }

  let session = findSessionById(sessionId)
  if (session) {
    return session
  }

  await loadSessions({ force: !sessionsLoaded.value })
  session = findSessionById(sessionId)
  if (session) {
    return session
  }

  await loadSessions({ force: true })
  return findSessionById(sessionId)
}

async function createSession(payload: { title: string, doc_type: string | null }) {
  const { data } = await apiChat.createSession(payload)
  upsertSession(data, { moveToFront: true })
  rememberLastSession(data.id)
  return data
}

async function updateSessionTitle(sessionId: number, title: string) {
  const { data } = await apiChat.updateSession(sessionId, { title })
  return upsertSession(data)
}

async function removeSession(sessionId: number) {
  await apiChat.deleteSession(sessionId)
  sessions.value = sessions.value.filter(session => Number(session.id) !== Number(sessionId))
  if (lastOpenedSessionId.value === Number(sessionId)) {
    rememberLastSession(null)
  }
}

export function useWritingSessions() {
  return {
    filteredSessions,
    findSessionById,
    ensureSessionById,
    createSession,
    lastOpenedSession,
    lastOpenedSessionId,
    loadSessions,
    loadingSessions,
    rememberLastSession,
    removeSession,
    sessionKeyword,
    sessions,
    setKeyword,
    updateSessionTitle,
  }
}

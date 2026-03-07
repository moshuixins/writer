import { addCollection, getIcon } from '@iconify/vue'
import iconifyConfig from './index.json'

interface OfflineIconifyConfig {
  collections: string[]
  isOfflineUse: boolean
}

const config = iconifyConfig as OfflineIconifyConfig
const configuredCollections = new Set(config.collections)
const loadedCollections = new Set<string>()
const pendingCollections = new Map<string, Promise<void>>()

function resolvePrefix(iconName: string) {
  const normalized = iconName.trim()
  if (!normalized.includes(':')) {
    return null
  }

  const segments = normalized.startsWith('@')
    ? normalized.slice(1).split(':')
    : normalized.split(':')

  if (segments.length < 2) {
    return null
  }

  return normalized.startsWith('@') ? segments[1] || null : segments[0] || null
}

function getOfflineIconUrl(prefix: string) {
  const baseUrl = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`

  return `${baseUrl}icons/${prefix}-raw.json`
}

export function isOfflineIconEnabled() {
  return config.isOfflineUse
}

export function isOfflineIconReady(iconName: string) {
  const prefix = resolvePrefix(iconName)
  if (!prefix) {
    return true
  }

  return loadedCollections.has(prefix) || !!getIcon(iconName)
}

export async function ensureOfflineIconCollection(iconName: string) {
  if (!config.isOfflineUse) {
    return
  }

  const prefix = resolvePrefix(iconName)
  if (!prefix || !configuredCollections.has(prefix)) {
    return
  }

  if (loadedCollections.has(prefix) || getIcon(iconName)) {
    loadedCollections.add(prefix)
    return
  }

  const currentTask = pendingCollections.get(prefix)
  if (currentTask) {
    await currentTask
    return
  }

  const task = (async () => {
    const response = await fetch(getOfflineIconUrl(prefix), {
      cache: 'force-cache',
    })
    if (!response.ok) {
      throw new Error(`Failed to load offline icon collection: ${prefix}`)
    }

    const data = Object.freeze(await response.json())
    addCollection(data)
    loadedCollections.add(prefix)
  })()

  pendingCollections.set(prefix, task)
  try {
    await task
  }
  finally {
    pendingCollections.delete(prefix)
  }
}

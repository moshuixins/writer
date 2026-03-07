<script setup lang="ts">
import type { Editor as TinyEditor } from 'tinymce'
import type { WriterDraft } from '@/types/writer'
import Editor from '@tinymce/tinymce-vue'
import { ElMessage } from 'element-plus'
import tinymce from 'tinymce'
import { onBeforeUnmount, ref, watch } from 'vue'
import 'tinymce/icons/default'
import 'tinymce/themes/silver'
import 'tinymce/models/dom'
import 'tinymce/skins/ui/oxide/skin.min.css'
import 'tinymce/skins/content/default/content.min.css'

const props = defineProps<{
  modelValue: WriterDraft
  saveStatus: string
  saving: boolean
  lastSavedAt: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: WriterDraft): void
  (e: 'manualSave'): void
  (e: 'quoteSelection', value: string): void
}>()

void tinymce

function defaultBodyJson() {
  return {
    type: 'doc',
    content: [{ type: 'paragraph' }],
  }
}

function normalizeBodyJson(body: unknown): Record<string, unknown> {
  if (!body || typeof body !== 'object') {
    return defaultBodyJson()
  }
  const asDoc = body as Record<string, unknown>
  if (asDoc.type !== 'doc' || !Array.isArray(asDoc.content)) {
    return defaultBodyJson()
  }
  return JSON.parse(JSON.stringify(asDoc))
}

function cloneDraft(draft: WriterDraft): WriterDraft {
  return {
    title: draft.title || '',
    recipients: draft.recipients || '',
    body_json: normalizeBodyJson(draft.body_json),
    signing_org: draft.signing_org || '',
    date: draft.date || '',
  }
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll('\'', '&#39;')
}

function normalizePlainText(text: string): string {
  return text.replaceAll('\u00A0', ' ')
}

function marksSignature(marks: Array<{ type: 'bold' | 'underline' }>): string {
  return marks.map(mark => mark.type).sort().join('|')
}

function withMark(
  marks: Array<{ type: 'bold' | 'underline' }>,
  type: 'bold' | 'underline',
): Array<{ type: 'bold' | 'underline' }> {
  if (marks.some(mark => mark.type === type)) {
    return marks
  }
  return [...marks, { type }]
}

function pushTextNode(
  target: Array<Record<string, unknown>>,
  text: string,
  marks: Array<{ type: 'bold' | 'underline' }>,
) {
  if (!text) {
    return
  }

  const nextNode: Record<string, unknown> = {
    type: 'text',
    text,
  }

  if (marks.length) {
    nextNode.marks = marks.map(mark => ({ type: mark.type }))
  }

  const last = target[target.length - 1]
  if (!last || last.type !== 'text') {
    target.push(nextNode)
    return
  }

  const lastMarks = Array.isArray(last.marks)
    ? (last.marks as Array<{ type?: string }>)
        .filter(mark => mark?.type === 'bold' || mark?.type === 'underline')
        .map(mark => ({ type: mark.type as 'bold' | 'underline' }))
    : []

  if (marksSignature(lastMarks) === marksSignature(marks)) {
    last.text = `${String(last.text || '')}${text}`
    return
  }

  target.push(nextNode)
}

function textToInlineNodes(
  text: string,
  marks: Array<{ type: 'bold' | 'underline' }>,
  target: Array<Record<string, unknown>>,
) {
  const normalizedText = normalizePlainText(text)
  if (!normalizedText.trim()) {
    return
  }

  const parts = normalizedText.replaceAll('\r\n', '\n').split('\n')
  parts.forEach((part, index) => {
    if (part) {
      pushTextNode(target, part, marks)
    }
    if (index < parts.length - 1) {
      target.push({ type: 'hardBreak' })
    }
  })
}

function parseInlineDom(
  node: Node,
  marks: Array<{ type: 'bold' | 'underline' }>,
  target: Array<Record<string, unknown>>,
) {
  if (node.nodeType === Node.TEXT_NODE) {
    textToInlineNodes(node.textContent || '', marks, target)
    return
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return
  }

  const element = node as HTMLElement
  const tag = element.tagName.toLowerCase()

  if (tag === 'br') {
    target.push({ type: 'hardBreak' })
    return
  }

  let nextMarks = marks
  if (tag === 'strong' || tag === 'b') {
    nextMarks = withMark(nextMarks, 'bold')
  }
  else if (tag === 'u') {
    nextMarks = withMark(nextMarks, 'underline')
  }

  for (const child of Array.from(element.childNodes)) {
    parseInlineDom(child, nextMarks, target)
  }
}

function parseInlineChildren(element: HTMLElement): Array<Record<string, unknown>> {
  const nodes: Array<Record<string, unknown>> = []
  for (const child of Array.from(element.childNodes)) {
    parseInlineDom(child, [], nodes)
  }
  return nodes
}

function bodyJsonToHtml(body: unknown): string {
  const normalized = normalizeBodyJson(body)
  const rootContent = Array.isArray(normalized.content) ? normalized.content : []

  const blocks = rootContent.map((node) => {
    if (!node || typeof node !== 'object') {
      return ''
    }

    const block = node as Record<string, unknown>
    const inline = inlineNodesToHtml(block.content)

    if (block.type === 'heading') {
      const attrs = (block.attrs && typeof block.attrs === 'object') ? block.attrs as Record<string, unknown> : {}
      const parsedLevel = Number(attrs.level)
      const level = parsedLevel === 1 || parsedLevel === 2 || parsedLevel === 3 ? parsedLevel : 2
      return `<h${level}>${inline || '<br />'}</h${level}>`
    }

    if (block.type === 'paragraph') {
      return `<p>${inline || '<br />'}</p>`
    }

    return ''
  }).filter(Boolean)

  return blocks.length ? blocks.join('') : '<p><br /></p>'
}

function inlineNodesToHtml(nodes: unknown): string {
  if (!Array.isArray(nodes)) {
    return ''
  }

  return nodes.map((node) => {
    if (!node || typeof node !== 'object') {
      return ''
    }

    const current = node as Record<string, unknown>

    if (current.type === 'hardBreak') {
      return '<br />'
    }

    if (current.type === 'text') {
      let chunk = escapeHtml(String(current.text || ''))
      const marks = Array.isArray(current.marks) ? current.marks : []
      for (const mark of marks) {
        if (!mark || typeof mark !== 'object') {
          continue
        }
        const markType = (mark as Record<string, unknown>).type
        if (markType === 'bold') {
          chunk = `<strong>${chunk}</strong>`
        }
        else if (markType === 'underline') {
          chunk = `<u>${chunk}</u>`
        }
      }
      return chunk
    }

    return inlineNodesToHtml(current.content)
  }).join('')
}

function sameBodyJson(a: unknown, b: unknown): boolean {
  return JSON.stringify(normalizeBodyJson(a)) === JSON.stringify(normalizeBodyJson(b))
}

function htmlToBodyJson(html: string): Record<string, unknown> {
  const container = window.document.createElement('div')
  container.innerHTML = html || ''
  const content: Array<Record<string, unknown>> = []

  for (const node of Array.from(container.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE) {
      const raw = normalizePlainText(node.textContent || '')
      if (!raw.trim()) {
        continue
      }
      const lines = raw.replaceAll('\r\n', '\n').split('\n')
      for (const line of lines) {
        const text = line.trim()
        if (!text) {
          continue
        }
        content.push({
          type: 'paragraph',
          content: [{ type: 'text', text }],
        })
      }
      continue
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      continue
    }

    const element = node as HTMLElement
    const tag = element.tagName.toLowerCase()

    if (tag === 'h1' || tag === 'h2' || tag === 'h3') {
      const inline = parseInlineChildren(element)
      content.push({
        type: 'heading',
        attrs: { level: tag === 'h1' ? 1 : tag === 'h2' ? 2 : 3 },
        ...(inline.length ? { content: inline } : {}),
      })
      continue
    }

    if (tag === 'p' || tag === 'div' || tag === 'section' || tag === 'article' || tag === 'blockquote' || tag === 'li') {
      const inline = parseInlineChildren(element)
      content.push({
        type: 'paragraph',
        ...(inline.length ? { content: inline } : {}),
      })
      continue
    }

    if (tag === 'ul' || tag === 'ol') {
      const items = Array.from(element.querySelectorAll(':scope > li'))
      if (!items.length) {
        content.push({ type: 'paragraph' })
      }
      else {
        for (const item of items) {
          const inline = parseInlineChildren(item as HTMLElement)
          content.push({
            type: 'paragraph',
            ...(inline.length ? { content: inline } : {}),
          })
        }
      }
      continue
    }

    const fallbackText = normalizePlainText(element.textContent || '').trim()
    if (fallbackText) {
      content.push({
        type: 'paragraph',
        content: [{ type: 'text', text: fallbackText }],
      })
    }
  }

  return {
    type: 'doc',
    content: content.length ? content : [{ type: 'paragraph' }],
  }
}

const syncingFromParent = ref(false)
const applyingEditorContent = ref(false)
const internalDraft = ref<WriterDraft>(cloneDraft(props.modelValue))
const editorHtml = ref<string>(bodyJsonToHtml(internalDraft.value.body_json))
const editorInstance = ref<TinyEditor | null>(null)

type BlockTag = 'p' | 'h1' | 'h2' | 'h3'

function registerBlockButton(editor: TinyEditor, name: string, label: string, tag: BlockTag) {
  editor.ui.registry.addToggleButton(name, {
    text: label,
    onAction: () => {
      editor.execCommand('FormatBlock', false, tag)
    },
    onSetup: (api) => {
      const updateActive = () => {
        const start = editor.selection.getStart(true) as HTMLElement | null
        const block = start ? editor.dom.getParent(start, 'p,h1,h2,h3') : null
        api.setActive((block?.nodeName || '').toLowerCase() === tag)
      }
      editor.on('NodeChange SetContent', updateActive)
      updateActive()
      return () => {
        editor.off('NodeChange SetContent', updateActive)
      }
    },
  })
}

const editorInit = {
  license_key: 'gpl',
  menubar: false,
  height: '100%',
  toolbar: 'undo redo | format_p format_h1 format_h2 format_h3 | bold underline | removeformat',
  toolbar_mode: 'wrap',
  statusbar: false,
  branding: false,
  promotion: false,
  resize: false,
  skin: false,
  content_css: false,
  paste_as_text: true,
  forced_root_block: 'p',
  valid_elements: 'p,h1,h2,h3,strong/b,u,br',
  valid_styles: {},
  setup: (editor: TinyEditor) => {
    registerBlockButton(editor, 'format_p', 'p', 'p')
    registerBlockButton(editor, 'format_h1', 'h1', 'h1')
    registerBlockButton(editor, 'format_h2', 'h2', 'h2')
    registerBlockButton(editor, 'format_h3', 'h3', 'h3')
  },
  content_style: `
    body {
      margin: 0;
      padding: 20px;
      font-family: FangSong, "仿宋", serif;
      font-size: 16px;
      line-height: 1.85;
      color: #111827;
    }
    p {
      margin: 0 0 10px;
      text-indent: 2em;
    }
    h1 {
      margin: 16px 0 10px;
      text-indent: 0;
      text-align: center;
      font-size: 20px;
      font-weight: 700;
      font-family: SimHei, "黑体", sans-serif;
    }
    h2 {
      margin: 14px 0 10px;
      text-indent: 2em;
      font-size: 17px;
      font-family: SimHei, "黑体", sans-serif;
      font-weight: 700;
    }
    h3 {
      margin: 12px 0 8px;
      text-indent: 2em;
      font-size: 16px;
      font-family: KaiTi, "楷体", serif;
      font-weight: 600;
    }
  `,
}

function handleEditorInit(_event: unknown, editor: TinyEditor) {
  editorInstance.value = editor
  editorHtml.value = editor.getContent() || editorHtml.value
}

watch(
  () => props.modelValue,
  (value) => {
    syncingFromParent.value = true
    const prevBody = normalizeBodyJson(internalDraft.value.body_json)
    const nextDraft = cloneDraft(value)
    const nextBody = normalizeBodyJson(nextDraft.body_json)
    const fromExternal = !sameBodyJson(prevBody, nextBody)
    internalDraft.value = nextDraft

    if (!fromExternal) {
      syncingFromParent.value = false
      return
    }

    const nextHtml = bodyJsonToHtml(nextBody)

    const editor = editorInstance.value
    if (editor) {
      const currentBody = htmlToBodyJson(editor.getContent() || '')
      if (JSON.stringify(currentBody) !== JSON.stringify(nextBody)) {
        applyingEditorContent.value = true
        editor.setContent(nextHtml)
        editorHtml.value = editor.getContent() || nextHtml
        applyingEditorContent.value = false
      }
    }
    else {
      editorHtml.value = nextHtml
    }

    syncingFromParent.value = false
  },
  { deep: true },
)

watch(
  editorHtml,
  (value, prev) => {
    if (value === prev) {
      return
    }
    if (applyingEditorContent.value || syncingFromParent.value) {
      return
    }
    emitChange()
  },
)

function emitChange() {
  const next: WriterDraft = {
    ...internalDraft.value,
    body_json: htmlToBodyJson(editorHtml.value || ''),
  }
  internalDraft.value = next
  emit('update:modelValue', cloneDraft(next))
}

function insertTextAtCursor(text: string) {
  const editor = editorInstance.value
  if (!editor || !text.trim()) {
    return
  }

  const lines = text
    .replaceAll('\r\n', '\n')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    return
  }

  const html = lines.map(line => `<p>${escapeHtml(line)}</p>`).join('')
  editor.focus()
  editor.insertContent(html)
  editorHtml.value = editor.getContent() || editorHtml.value
  emitChange()
}

function getSelectionText() {
  if (!editorInstance.value) {
    return ''
  }
  return editorInstance.value.selection.getContent({ format: 'text' }).trim()
}

function emitQuoteSelection() {
  const selectedText = getSelectionText()
  if (!selectedText) {
    ElMessage.warning('请先在编辑器中选中文本')
    return
  }
  emit('quoteSelection', selectedText)
}

function focusEditor() {
  editorInstance.value?.focus()
}

defineExpose({
  insertTextAtCursor,
  getSelectionText,
  focusEditor,
})

onBeforeUnmount(() => {
  const editor = editorInstance.value
  if (editor) {
    try {
      if (!editor.removed) {
        editor.destroy()
      }
    }
    catch {
      // no-op
    }
  }
  editorInstance.value = null
})
</script>

<template>
  <div class="official-editor">
    <div class="editor-head">
      <div class="save-indicator" :class="{ saving }">
        <span>{{ saveStatus }}</span>
        <span v-if="lastSavedAt" class="saved-at">{{ lastSavedAt }}</span>
      </div>
      <div class="head-actions">
        <el-button size="small" type="primary" plain :loading="saving" @click="emit('manualSave')">
          手动保存
        </el-button>
        <el-button size="small" @click="emitQuoteSelection">
          引用选中文本到对话
        </el-button>
      </div>
    </div>

    <div class="editor-surface">
      <Editor
        v-model="editorHtml"
        model-events="change input undo redo"
        license-key="gpl"
        :init="editorInit"
        class="tinymce-body"
        @on-init="handleEditorInit"
      />
    </div>
  </div>
</template>

<style scoped>
.official-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  padding: 12px;
  background: var(--el-bg-color);
}

.editor-head {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.save-indicator {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.save-indicator.saving {
  color: var(--el-color-primary);
}

.saved-at {
  color: var(--el-text-color-placeholder);
}

.head-actions {
  display: flex;
  gap: 8px;
}

.editor-surface {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.editor-surface :deep(.tox),
.editor-surface :deep(.tox-tinymce) {
  flex: 1 1 auto;
  height: 100% !important;
  max-height: none;
}

.editor-surface :deep(.tox-tinymce) {
  display: flex;
  visibility: visible !important;
  flex-direction: column;
  min-height: 0;
  border: none;
  border-radius: inherit;
  box-shadow: none;
}

.editor-surface :deep(.tox-editor-container),
.editor-surface :deep(.tox-sidebar-wrap),
.editor-surface :deep(.tox-edit-area) {
  flex: 1;
  min-height: 0;
}

.editor-surface :deep(.tox-edit-area) {
  padding: 0;
}

.editor-surface :deep(.tox .tox-editor-header) {
  background: var(--w-color-white);
  border-bottom: 1px solid var(--w-gray-200);
}

.editor-surface :deep(.tox .tox-toolbar-overlord),
.editor-surface :deep(.tox .tox-toolbar__primary) {
  background: var(--w-color-white);
}

.editor-surface :deep(.tox .tox-toolbar__group) {
  gap: 6px;
  padding: 0 8px 0 0;
  margin-right: 8px;
  border-right: 1px solid var(--w-gray-200);
}

.editor-surface :deep(.tox .tox-toolbar__group:last-child) {
  padding-right: 0;
  margin-right: 0;
  border-right: none;
}

.editor-surface :deep(.tox .tox-tbtn) {
  box-sizing: border-box;
  min-width: 32px;
  height: 32px;
  padding: 0 11px;
  color: var(--w-btn-secondary-text);
  background: var(--w-btn-secondary-bg);
  border: 1px solid var(--w-btn-secondary-border);
  border-radius: var(--el-border-radius-base);
  box-shadow: none;
}

.editor-surface :deep(.tox .tox-tbtn .tox-tbtn__select-label) {
  font-family: var(--el-font-family);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: 0;
}

.editor-surface :deep(.tox .tox-tbtn:hover) {
  color: var(--w-btn-secondary-text);
  background: var(--w-btn-secondary-hover-bg);
  border-color: var(--w-btn-secondary-border);
}

.editor-surface :deep(.tox .tox-tbtn.tox-tbtn--enabled),
.editor-surface :deep(.tox .tox-tbtn[aria-pressed="true"]) {
  color: var(--w-btn-secondary-text);
  background: var(--w-btn-secondary-active-bg);
  border-color: var(--w-btn-secondary-border);
}

.editor-surface :deep(.tox .tox-tbtn svg) {
  fill: currentcolor;
}

@media (max-width: 900px) {
  .official-editor {
    padding: 8px;
  }

  .editor-head {
    flex-direction: column;
    align-items: stretch;
  }

  .head-actions {
    justify-content: flex-end;
  }
}
</style>

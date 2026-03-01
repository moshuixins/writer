<template>
  <div class="official-editor">
    <div class="editor-head">
      <div class="save-indicator" :class="{ saving }">
        <span>{{ saveStatus }}</span>
        <span v-if="lastSavedAt" class="saved-at">{{ lastSavedAt }}</span>
      </div>
      <div class="head-actions">
        <el-button size="small" type="primary" plain :loading="saving" @click="emit('manual-save')">
          手动保存
        </el-button>
        <el-button size="small" @click="emitQuoteSelection">
          引用选中文本到对话
        </el-button>
      </div>
    </div>

    <div class="meta-grid">
      <div class="meta-item title">
        <label>标题</label>
        <el-input
          v-model="internalDraft.title"
          placeholder="例如：关于开展交通秩序整治行动的通知"
          maxlength="100"
          @input="onMetaChange"
        />
      </div>
      <div class="meta-item recipients">
        <label>主送机关</label>
        <el-input
          v-model="internalDraft.recipients"
          placeholder="例如：各大队、机关各科室"
          maxlength="200"
          @input="onMetaChange"
        />
      </div>
      <div class="meta-item signing-org">
        <label>落款单位</label>
        <el-input
          v-model="internalDraft.signing_org"
          placeholder="例如：XX市公安局交通管理支队"
          maxlength="100"
          @input="onMetaChange"
        />
      </div>
      <div class="meta-item date">
        <label>日期</label>
        <el-input
          v-model="internalDraft.date"
          placeholder="例如：2026年3月1日"
          maxlength="50"
          @input="onMetaChange"
        />
      </div>
    </div>

    <div class="toolbar">
      <el-button-group>
        <el-button
          size="small"
          :type="isActiveParagraph ? 'primary' : 'default'"
          @click="setParagraph"
        >
          正文
        </el-button>
        <el-button
          size="small"
          :type="isActiveHeading2 ? 'primary' : 'default'"
          @click="setHeading(2)"
        >
          二级标题
        </el-button>
        <el-button
          size="small"
          :type="isActiveHeading3 ? 'primary' : 'default'"
          @click="setHeading(3)"
        >
          三级标题
        </el-button>
      </el-button-group>
      <el-button-group>
        <el-button
          size="small"
          :type="isActiveBold ? 'primary' : 'default'"
          @click="toggleBold"
        >
          加粗
        </el-button>
        <el-button
          size="small"
          :type="isActiveUnderline ? 'primary' : 'default'"
          @click="toggleUnderline"
        >
          下划线
        </el-button>
      </el-button-group>
    </div>

    <div class="editor-surface">
      <EditorContent v-if="editor" :editor="editor" class="tiptap-body" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import Bold from '@tiptap/extension-bold'
import Document from '@tiptap/extension-document'
import HardBreak from '@tiptap/extension-hard-break'
import Heading from '@tiptap/extension-heading'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import Underline from '@tiptap/extension-underline'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import type { WriterDraft } from '@/types/writer'

const props = defineProps<{
  modelValue: WriterDraft
  saveStatus: string
  saving: boolean
  lastSavedAt: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: WriterDraft): void
  (e: 'manual-save'): void
  (e: 'quote-selection', value: string): void
}>()

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

const syncingFromParent = ref(false)
const applyingEditorContent = ref(false)
const internalDraft = ref<WriterDraft>(cloneDraft(props.modelValue))

const editor = useEditor({
  content: internalDraft.value.body_json,
  extensions: [
    Document,
    Paragraph,
    Text,
    Heading.configure({ levels: [2, 3] }),
    Bold,
    Underline,
    HardBreak,
  ],
  autofocus: false,
  editorProps: {
    attributes: {
      class: 'official-doc-content',
      spellcheck: 'false',
    },
  },
  onUpdate: () => {
    if (applyingEditorContent.value || syncingFromParent.value) {
      return
    }
    emitChange()
  },
})

watch(
  () => props.modelValue,
  (value) => {
    syncingFromParent.value = true
    internalDraft.value = cloneDraft(value)

    const nextBody = normalizeBodyJson(value.body_json)
    if (editor.value) {
      const current = JSON.stringify(editor.value.getJSON())
      const next = JSON.stringify(nextBody)
      if (current !== next) {
        applyingEditorContent.value = true
        editor.value.commands.setContent(nextBody, false)
        applyingEditorContent.value = false
      }
    }

    syncingFromParent.value = false
  },
  { deep: true },
)

function emitChange() {
  const next: WriterDraft = {
    ...internalDraft.value,
    body_json: editor.value?.getJSON() as Record<string, unknown> || normalizeBodyJson(internalDraft.value.body_json),
  }
  internalDraft.value = next
  emit('update:modelValue', cloneDraft(next))
}

function onMetaChange() {
  if (syncingFromParent.value) {
    return
  }
  emitChange()
}

function toggleBold() {
  editor.value?.chain().focus().toggleBold().run()
}

function toggleUnderline() {
  editor.value?.chain().focus().toggleUnderline().run()
}

function setParagraph() {
  editor.value?.chain().focus().setParagraph().run()
}

function setHeading(level: 2 | 3) {
  editor.value?.chain().focus().setHeading({ level }).run()
}

function textToInsertContent(text: string) {
  const lines = text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    return [{ type: 'paragraph', content: [{ type: 'text', text: text.trim() }] }]
  }

  return lines.map(line => ({
    type: 'paragraph',
    content: [{ type: 'text', text: line }],
  }))
}

function insertTextAtCursor(text: string) {
  if (!editor.value || !text.trim()) {
    return
  }

  editor.value.chain().focus().insertContent(textToInsertContent(text)).run()
  emitChange()
}

function getSelectionText() {
  if (!editor.value) {
    return ''
  }

  const { from, to } = editor.value.state.selection
  if (from === to) {
    return ''
  }

  return editor.value.state.doc.textBetween(from, to, '\n').trim()
}

function emitQuoteSelection() {
  const selectedText = getSelectionText()
  if (!selectedText) {
    ElMessage.warning('请先在编辑器中选中文本')
    return
  }
  emit('quote-selection', selectedText)
}

function focusEditor() {
  editor.value?.chain().focus().run()
}

const isActiveBold = computed(() => !!editor.value?.isActive('bold'))
const isActiveUnderline = computed(() => !!editor.value?.isActive('underline'))
const isActiveParagraph = computed(() => !!editor.value?.isActive('paragraph'))
const isActiveHeading2 = computed(() => !!editor.value?.isActive('heading', { level: 2 }))
const isActiveHeading3 = computed(() => !!editor.value?.isActive('heading', { level: 3 }))

defineExpose({
  insertTextAtCursor,
  getSelectionText,
  focusEditor,
})

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.official-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  padding: 12px;
  background: linear-gradient(180deg, #fdfdfd 0%, #f8fafc 100%);
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.save-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item.title,
.meta-item.recipients {
  grid-column: span 2;
}

.meta-item label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  background: #fff;
}

.editor-surface {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.tiptap-body {
  height: 100%;
}

.tiptap-body :deep(.official-doc-content) {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  outline: none;
  font-family: 'FangSong', '仿宋', serif;
  font-size: 16px;
  line-height: 1.85;
  color: #111827;
}

.tiptap-body :deep(p) {
  margin: 0 0 10px;
  text-indent: 2em;
}

.tiptap-body :deep(h2) {
  margin: 14px 0 10px;
  text-indent: 2em;
  font-size: 17px;
  font-family: 'SimHei', '黑体', sans-serif;
  font-weight: 700;
}

.tiptap-body :deep(h3) {
  margin: 12px 0 8px;
  text-indent: 2em;
  font-size: 16px;
  font-family: 'KaiTi', '楷体', serif;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }

  .meta-item.title,
  .meta-item.recipients {
    grid-column: span 1;
  }
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

  .toolbar {
    flex-wrap: wrap;
  }
}
</style>

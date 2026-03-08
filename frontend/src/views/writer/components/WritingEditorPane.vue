<script setup lang="ts">
import type { ChatSession, WriterDraft } from '@/types/writer'
import { defineAsyncComponent, ref } from 'vue'
import EmptyState from '@/components/EmptyState/index.vue'

interface OfficialEditorExpose {
  focusEditor: () => void
  insertTextAtCursor: (text: string) => void
}

defineProps<{
  currentSession: ChatSession | null
  lastSavedAt: string
  loadingDraft: boolean
  modelValue: WriterDraft
  saveStatus: string
  saving: boolean
}>()

const emit = defineEmits<{
  (e: 'manualSave'): void
  (e: 'quoteSelection', value: string): void
  (e: 'update:modelValue', value: WriterDraft): void
}>()

const OfficialDocEditor = defineAsyncComponent(() => import('./OfficialDocEditor.vue'))

const editorRef = ref<OfficialEditorExpose | null>(null)

function focusEditor() {
  editorRef.value?.focusEditor()
}

function insertTextAtCursor(text: string) {
  editorRef.value?.insertTextAtCursor(text)
}

defineExpose({
  focusEditor,
  insertTextAtCursor,
})
</script>

<template>
  <div class="writing-editor-pane">
    <template v-if="!currentSession">
      <EmptyState
        icon="i-ep:document"
        title="请先选择会话"
        description="进入某个写作会话后，编辑器会加载当前草稿，并支持自动保存与引用选中文本。"
      />
    </template>
    <template v-else-if="loadingDraft">
      <el-skeleton :rows="8" animated class="writing-editor-pane__skeleton" />
    </template>
    <template v-else>
      <Suspense>
        <OfficialDocEditor
          ref="editorRef"
          class="writing-editor-pane__body"
          :model-value="modelValue"
          :save-status="saveStatus"
          :saving="saving"
          :last-saved-at="lastSavedAt"
          @update:model-value="value => emit('update:modelValue', value)"
          @manual-save="emit('manualSave')"
          @quote-selection="value => emit('quoteSelection', value)"
        />
        <template #fallback>
          <el-skeleton :rows="8" animated class="writing-editor-pane__body writing-editor-pane__skeleton" />
        </template>
      </Suspense>
    </template>
  </div>
</template>

<style scoped>
.writing-editor-pane {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.writing-editor-pane__body {
  flex: 1;
  min-height: 0;
}

.writing-editor-pane__skeleton {
  padding: 12px;
}
</style>

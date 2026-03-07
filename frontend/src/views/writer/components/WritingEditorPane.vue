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
    <div class="writing-editor-pane__meta">
      <h3 class="writing-editor-pane__title">
        ?????
      </h3>
      <span v-if="currentSession" class="writing-editor-pane__hint">????????</span>
    </div>

    <template v-if="!currentSession">
      <EmptyState
        icon="i-ep:document"
        title="??????"
        description="??????????????????????????????"
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
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.writing-editor-pane__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.writing-editor-pane__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.writing-editor-pane__hint {
  font-size: 12px;
  color: var(--w-text-secondary);
}

.writing-editor-pane__body {
  flex: 1;
  min-height: 0;
}

.writing-editor-pane__skeleton {
  padding: 12px;
}
</style>

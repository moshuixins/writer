<script setup lang="ts">
defineProps<{
  modelValue: 'chat' | 'editor'
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: 'chat' | 'editor'): void
}>()

function handleUpdate(value: string | number | boolean | undefined) {
  if (value === 'chat' || value === 'editor') {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <div class="writing-mobile-switch">
    <el-radio-group :model-value="modelValue" size="small" @update:model-value="handleUpdate">
      <el-radio-button value="chat">
        对话区
      </el-radio-button>
      <el-radio-button value="editor">
        文稿区
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<style scoped>
.writing-mobile-switch {
  display: flex;
  justify-content: flex-start;
  padding: 2px;
}

.writing-mobile-switch :deep(.el-radio-group) {
  padding: 4px;
  background: rgb(255 253 249 / 88%);
  border: 1px solid var(--w-divider);
  border-radius: 14px;
}
</style>

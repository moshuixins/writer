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
      <el-radio-button label="chat">
        对话
      </el-radio-button>
      <el-radio-button label="editor">
        文稿
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<style scoped>
.writing-mobile-switch {
  display: flex;
  justify-content: flex-start;
}
</style>

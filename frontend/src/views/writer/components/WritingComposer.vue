<script setup lang="ts">
defineProps<{
  modelValue: string
  sending: boolean
  hasSession: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send'): void
  (e: 'stop'): void
  (e: 'export'): void
}>()
</script>

<template>
  <div class="writing-composer">
    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="4"
      placeholder="输入写作诉求或修改意见…（Ctrl+Enter 发送）"
      resize="none"
      @update:model-value="value => emit('update:modelValue', String(value))"
      @keyup.ctrl.enter="emit('send')"
    />
    <div class="writing-composer__actions">
      <el-button type="primary" :loading="sending" :disabled="sending || !modelValue.trim()" @click="emit('send')">
        发送请求
      </el-button>
      <el-button v-if="sending" @click="emit('stop')">
        停止生成
      </el-button>
      <el-button :disabled="!hasSession || sending" @click="emit('export')">
        导出 docx
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.writing-composer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--w-divider);
}

.writing-composer__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>

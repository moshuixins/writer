<script setup lang="ts">
import type { ChatWorkflowStep } from '@/types/writer'

defineProps<{
  steps: ChatWorkflowStep[]
}>()
</script>

<template>
  <div class="writing-workflow-card">
    <div class="writing-workflow-card__title">
      AI 工作流程
    </div>
    <div
      v-for="step in steps"
      :key="step.id"
      class="writing-workflow-card__item"
      :class="`is-${step.status}`"
    >
      <span class="writing-workflow-card__dot" />
      <span class="writing-workflow-card__text">{{ step.step }}</span>
      <span v-if="step.detail" class="writing-workflow-card__detail">{{ step.detail }}</span>
    </div>
  </div>
</template>

<style scoped>
.writing-workflow-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  background: var(--w-gray-50);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-md);
}

.writing-workflow-card__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--w-text-secondary);
}

.writing-workflow-card__item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.writing-workflow-card__dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  background: var(--w-gray-300);
  border-radius: 999px;
}

.writing-workflow-card__text {
  font-size: 13px;
  color: var(--w-text-primary);
}

.writing-workflow-card__detail {
  grid-column: 2;
  font-size: 12px;
  color: var(--w-text-tertiary);
}

.is-running .writing-workflow-card__dot {
  background: var(--w-workflow-running);
}

.is-done .writing-workflow-card__dot {
  background: var(--w-workflow-done);
}

.is-error .writing-workflow-card__dot {
  background: var(--w-workflow-error);
}
</style>

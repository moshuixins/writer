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
    <div class="writing-workflow-card__steps">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="writing-workflow-card__item"
        :class="`is-${step.status}`"
      >
        <span class="writing-workflow-card__index">{{ index + 1 }}</span>
        <div class="writing-workflow-card__content">
          <span class="writing-workflow-card__text">{{ step.step }}</span>
          <span v-if="step.detail" class="writing-workflow-card__detail">{{ step.detail }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.writing-workflow-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: #f5f1e8;
  border: 1px solid #e3ded4;
  border-radius: 16px;
}

.writing-workflow-card__title {
  font-size: 12px;
  font-weight: 700;
  color: var(--w-text-secondary);
}

.writing-workflow-card__steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.writing-workflow-card__item {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.writing-workflow-card__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font-size: 11px;
  font-weight: 700;
  color: var(--w-text-secondary);
  background: rgb(255 255 255 / 88%);
  border: 1px solid rgb(92 85 76 / 12%);
  border-radius: 999px;
}

.writing-workflow-card__content {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 2px;
}

.writing-workflow-card__text {
  font-size: 13px;
  font-weight: 600;
  color: var(--w-text-primary);
}

.writing-workflow-card__detail {
  font-size: 12px;
  line-height: 1.55;
  color: var(--w-text-tertiary);
}

.is-running .writing-workflow-card__index {
  color: var(--w-state-warning-text);
  background: var(--w-state-warning-bg);
  border-color: rgb(133 91 28 / 18%);
}

.is-done .writing-workflow-card__index {
  color: var(--w-state-success-text);
  background: var(--w-state-success-bg);
  border-color: rgb(36 86 56 / 18%);
}

.is-error .writing-workflow-card__index {
  color: var(--w-state-danger-text);
  background: var(--w-state-danger-bg);
  border-color: rgb(138 44 44 / 18%);
}
</style>

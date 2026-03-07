<script setup lang="ts">
import type { ChatMessage, ChatSession } from '@/types/writer'
import { CopyDocument, Download, Monitor, User } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState/index.vue'
import WritingWorkflowCard from './WritingWorkflowCard.vue'

const props = defineProps<{
  currentSession: ChatSession | null
  loading: boolean
  messages: ChatMessage[]
  renderMessage: (message: ChatMessage) => string
}>()

const emit = defineEmits<{
  (e: 'copy', value: string): void
  (e: 'insert', value: string): void
}>()

function renderMessage(message: ChatMessage) {
  return props.renderMessage(message)
}
</script>

<template>
  <div class="writing-message-list">
    <template v-if="loading">
      <el-skeleton :rows="4" animated class="writing-message-list__skeleton" />
    </template>
    <template v-else-if="!currentSession">
      <EmptyState
        icon="i-ep:chat-dot-round"
        title="请先选择或新建会话"
        description="选择左侧会话后，AI 对话、工作流和文稿草稿会同步进入当前工作区。"
      />
    </template>
    <template v-else-if="messages.length === 0">
      <EmptyState
        icon="i-ep:edit-pen"
        title="当前会话还没有消息"
        description="输入写作需求、修改意见或引用编辑器中的片段，即可开始生成。"
      />
    </template>
    <template v-else>
      <div
        v-for="message in messages"
        :key="message.id"
        class="writing-message-list__item"
        :class="[
          `is-${message.role}`,
          {
            'is-sending': message.id?.toString().startsWith('sending-') || message.id?.toString().startsWith('stream-'),
          },
        ]"
      >
        <div class="writing-message-list__avatar" :class="`is-${message.role}`">
          <el-icon v-if="message.role === 'assistant'">
            <Monitor />
          </el-icon>
          <el-icon v-else>
            <User />
          </el-icon>
        </div>
        <div class="writing-message-list__bubble-wrap">
          <WritingWorkflowCard
            v-if="message.role === 'assistant' && message.workflow_steps?.length"
            :steps="message.workflow_steps"
          />
          <div v-if="message.role === 'assistant'" class="writing-message-list__bubble markdown-body" v-html="renderMessage(message)" />
          <div v-else class="writing-message-list__bubble">
            {{ message.content }}
          </div>
          <div v-if="message.role === 'assistant' && (message.content || '').trim()" class="writing-message-list__actions">
            <el-button text size="small" @click="emit('copy', message.content)">
              <el-icon><CopyDocument /></el-icon>
              复制内容
            </el-button>
            <el-button text size="small" @click="emit('insert', message.content)">
              <el-icon><Download /></el-icon>
              插入文稿
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.writing-message-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100%;
}

.writing-message-list__skeleton {
  padding: 12px;
}

.writing-message-list__item {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
}

.writing-message-list__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  color: var(--w-text-primary);
  background: var(--w-gray-100);
  border-radius: 999px;
}

.writing-message-list__avatar.is-assistant {
  color: var(--w-color-white);
  background: var(--w-color-black);
}

.writing-message-list__bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.writing-message-list__bubble {
  padding: 14px 16px;
  line-height: 1.75;
  color: var(--w-text-primary);
  white-space: pre-wrap;
  background: var(--w-color-white);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-lg);
  box-shadow: var(--w-shadow-xs);
}

.is-user .writing-message-list__bubble {
  background: var(--w-message-user-bg);
}

.is-sending .writing-message-list__bubble {
  opacity: 0.72;
}

.writing-message-list__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>

<script setup lang="ts">
import type { ChatSession } from '@/types/writer'
import { Close, Edit, Plus } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState/index.vue'

const props = defineProps<{
  currentSessionId: number | null
  filteredSessions: ChatSession[]
  keyword: string
  loading: boolean
  sessions: ChatSession[]
  formatDate: (value: string) => string
}>()

const emit = defineEmits<{
  (e: 'create'): void
  (e: 'delete', id: number): void
  (e: 'rename', session: ChatSession): void
  (e: 'select', session: ChatSession): void
  (e: 'update:keyword', value: string): void
}>()

function formatDate(value: string) {
  return props.formatDate(value)
}
</script>

<template>
  <div class="writing-session-sidebar">
    <el-button type="primary" class="writing-session-sidebar__new" @click="emit('create')">
      <el-icon><Plus /></el-icon>
      <span>新建会话</span>
    </el-button>

    <el-input
      :model-value="keyword"
      class="writing-session-sidebar__search"
      clearable
      placeholder="搜索会话标题"
      @update:model-value="value => emit('update:keyword', String(value))"
    />

    <div class="writing-session-sidebar__list">
      <template v-if="loading">
        <el-skeleton :rows="4" animated class="writing-session-sidebar__skeleton" />
      </template>
      <template v-else-if="sessions.length === 0">
        <EmptyState title="暂无会话" description="点击上方“新建会话”即可开始新的写作任务。" />
      </template>
      <template v-else-if="filteredSessions.length === 0">
        <EmptyState title="没有匹配结果" description="可以尝试缩短关键词，或直接从现有会话中选择。" />
      </template>
      <template v-else>
        <button
          v-for="session in filteredSessions"
          :key="session.id"
          class="writing-session-sidebar__item"
          :class="{ 'is-active': currentSessionId === session.id }"
          type="button"
          @click="emit('select', session)"
        >
          <div class="writing-session-sidebar__item-main">
            <div class="writing-session-sidebar__item-title">
              {{ session.title }}
            </div>
            <div class="writing-session-sidebar__item-meta">
              <span>{{ formatDate(session.created_at) }}</span>
              <el-tag v-if="session.doc_type" size="small">
                {{ session.doc_type }}
              </el-tag>
            </div>
          </div>
          <div class="writing-session-sidebar__item-actions">
            <el-button text size="small" @click.stop="emit('rename', session)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button text size="small" @click.stop="emit('delete', session.id)">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.writing-session-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  min-height: 0;
}

.writing-session-sidebar__new {
  justify-content: center;
  width: 100%;
}

.writing-session-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
}

.writing-session-sidebar__skeleton {
  padding: 10px;
}

.writing-session-sidebar__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  width: 100%;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  background: var(--w-color-white);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-lg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.writing-session-sidebar__item:hover,
.writing-session-sidebar__item.is-active {
  border-color: var(--w-color-black);
  box-shadow: var(--w-shadow-sm);
}

.writing-session-sidebar__item.is-active {
  transform: translateY(-1px);
}

.writing-session-sidebar__item-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.writing-session-sidebar__item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 600;
  color: var(--w-text-primary);
  white-space: nowrap;
}

.writing-session-sidebar__item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--w-text-tertiary);
}

.writing-session-sidebar__item-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>

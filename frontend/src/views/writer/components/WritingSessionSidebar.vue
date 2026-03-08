<script setup lang="ts">
import type { ChatSession } from '@/types/writer'
import { Close, Edit, Plus } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState/index.vue'
import MetaTag from '@/components/MetaTag/index.vue'

withDefaults(defineProps<{
  currentSessionId: number | null
  filteredSessions: ChatSession[]
  formatDate: (value?: string | null) => string
  keyword: string
  loading: boolean
  sessions: ChatSession[]
  showCreateButton?: boolean
}>(), {
  showCreateButton: true,
})

const emit = defineEmits<{
  (e: 'create'): void
  (e: 'delete', id: number): void
  (e: 'rename', session: ChatSession): void
  (e: 'select', session: ChatSession): void
  (e: 'update:keyword', value: string): void
}>()
</script>

<template>
  <div class="writing-session-sidebar">
    <el-button v-if="showCreateButton" type="primary" class="writing-session-sidebar__new" @click="emit('create')">
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
        <EmptyState title="暂无会话" description="使用页面中的新建会话入口即可开始新的写作任务。" />
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
              <MetaTag v-if="session.doc_type" :label="session.doc_type" tone="muted" />
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

.writing-session-sidebar__search :deep(.el-input__wrapper) {
  background: rgb(255 253 249 / 82%);
  border-radius: 12px;
  box-shadow: inset 0 0 0 1px rgb(227 222 212 / 92%);
}

.writing-session-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  padding-right: 2px;
  overflow-y: auto;
}

.writing-session-sidebar__skeleton {
  padding: 10px;
}

.writing-session-sidebar__item {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  width: 100%;
  padding: 14px 14px 14px 16px;
  text-align: left;
  cursor: pointer;
  background: rgb(255 253 249 / 90%);
  border: 1px solid rgb(227 222 212 / 92%);
  border-radius: 16px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.writing-session-sidebar__item:hover {
  border-color: #d5cdbf;
  box-shadow: var(--w-shadow-xs);
}

.writing-session-sidebar__item.is-active {
  background: linear-gradient(180deg, #f7f3ea 0%, #f1ebe0 100%);
  border-color: #d6cebf;
  box-shadow: var(--w-shadow-sm);
}

.writing-session-sidebar__item.is-active::before {
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 8px;
  width: 3px;
  content: "";
  background: var(--w-color-black);
  border-radius: 999px;
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
  font-weight: 700;
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
  justify-content: space-between;
}
</style>

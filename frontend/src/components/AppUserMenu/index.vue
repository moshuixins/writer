<script setup lang="ts">
import { ArrowDown, Setting, SwitchButton } from '@element-plus/icons-vue'
import { computed } from 'vue'

const router = useRouter()
const userStore = useUserStore()

const displayName = computed(() => userStore.user?.display_name || userStore.account || '未登录用户')
const department = computed(() => userStore.user?.department || '未设置部门')

function openProfile() {
  void router.push('/settings')
}

function logout() {
  userStore.logout('/chat')
}
</script>

<template>
  <el-dropdown trigger="click" placement="bottom-end">
    <button class="app-user-menu" type="button">
      <span class="app-user-menu__avatar">{{ displayName.slice(0, 1) }}</span>
      <span class="app-user-menu__meta">
        <span class="app-user-menu__name">{{ displayName }}</span>
        <span class="app-user-menu__dept">{{ department }}</span>
      </span>
      <el-icon><ArrowDown /></el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item @click="openProfile">
          <el-icon><Setting /></el-icon>
          偏好设置
        </el-dropdown-item>
        <el-dropdown-item divided @click="logout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>
.app-user-menu {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
  padding: 8px 10px;
  color: var(--w-text-primary);
  cursor: pointer;
  background: var(--w-color-white);
  border: 1px solid var(--w-divider);
  border-radius: var(--w-radius-md);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.app-user-menu:hover {
  border-color: var(--w-gray-300);
  box-shadow: var(--w-shadow-xs);
}

.app-user-menu:focus-visible {
  outline: none;
  box-shadow: var(--w-focus-ring);
}

.app-user-menu__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 13px;
  font-weight: 700;
  color: var(--w-color-white);
  background: var(--w-color-black);
  border-radius: 999px;
}

.app-user-menu__meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  text-align: left;
}

.app-user-menu__name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.app-user-menu__dept {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: var(--w-text-secondary);
  white-space: nowrap;
}

@media (max-width: 768px) {
  .app-user-menu__meta {
    display: none;
  }
}
</style>

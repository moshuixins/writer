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
    <button class="app-user-menu" type="button" :aria-label="`用户菜单：${displayName}`">
      <span class="app-user-menu__avatar">{{ displayName.slice(0, 1) }}</span>
      <el-icon class="app-user-menu__arrow">
        <ArrowDown />
      </el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item disabled>
          <div class="app-user-menu__dropdown-meta">
            <strong>{{ displayName }}</strong>
            <span>{{ department }}</span>
          </div>
        </el-dropdown-item>
        <el-dropdown-item divided @click="openProfile">
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
  gap: 8px;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 5px 8px 5px 5px;
  color: var(--w-text-primary);
  cursor: pointer;
  background: rgb(255 253 249 / 82%);
  border: 1px solid var(--w-divider);
  border-radius: 999px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
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
  width: 34px;
  height: 34px;
  font-size: 13px;
  font-weight: 700;
  color: var(--w-color-white);
  background: var(--w-color-black);
  border-radius: 999px;
}

.app-user-menu__arrow {
  font-size: 14px;
  color: var(--w-text-secondary);
}

.app-user-menu__dropdown-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 180px;
  line-height: 1.45;
}

.app-user-menu__dropdown-meta strong {
  font-size: 13px;
  color: var(--w-text-primary);
}

.app-user-menu__dropdown-meta span {
  font-size: 12px;
  color: var(--w-text-secondary);
}
</style>

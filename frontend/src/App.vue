<template>
  <el-container class="app-container" v-if="authStore.isLoggedIn">
    <el-aside width="220px">
      <div class="logo">
        <span class="logo-icon">&#9998;</span>
        <span>公文写作助手</span>
      </div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#1d2b3a"
        text-color="#a0aec0"
        active-text-color="#fff"
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>写作对话</span>
        </el-menu-item>
        <el-menu-item index="/materials">
          <el-icon><Document /></el-icon>
          <span>素材管理</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><FolderOpened /></el-icon>
          <span>导出历史</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>偏好设置</span>
        </el-menu-item>
      </el-menu>
      <div class="user-info">
        <span class="username">{{ authStore.user?.display_name || authStore.user?.username }}</span>
        <el-button text size="small" class="logout-btn" @click="handleLogout">退出</el-button>
      </div>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
  <router-view v-else />
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import {
  Document,
  ChatDotRound,
  Setting,
  FolderOpened,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

authStore.restoreUser()

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  authStore.logout()
  router.push('/login')
}
</script>

<style>
html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
#app { height: 100%; }
.app-container { height: 100vh; }
.el-aside { background-color: #1d2b3a; position: relative; overflow: hidden; }
.logo {
  color: #fff; font-size: 17px; font-weight: 600;
  padding: 20px 16px; text-align: center;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-icon { font-size: 20px; }
.el-main { padding: 0; background: #f5f7fa; }
.el-menu { border-right: none !important; }
.el-menu-item { margin: 4px 8px; border-radius: 8px; }
.el-menu-item.is-active { background: rgba(64,158,255,0.15) !important; }
.user-info {
  position: absolute; bottom: 0; width: 100%;
  padding: 14px 16px; box-sizing: border-box;
  display: flex; justify-content: space-between; align-items: center;
  border-top: 1px solid rgba(255,255,255,0.08);
  background: rgba(0,0,0,0.1);
}
.user-info .username { color: #a0aec0; font-size: 13px; }
.logout-btn { color: #a0aec0 !important; }
.logout-btn:hover { color: #f56c6c !important; }
</style>

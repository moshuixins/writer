<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <span class="login-icon">&#9998;</span>
        <h2>公文写作助手</h2>
        <p class="subtitle">交管支队智能写作平台</p>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码"
                :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleLogin">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（至少2个字符）" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.display_name" placeholder="显示名称（选填）" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码（至少6位）"
                :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.confirmPassword" type="password" placeholder="确认密码"
                :prefix-icon="Lock" show-password @keyup.enter="handleRegister" />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleRegister">
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref('login')
const loading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '', confirmPassword: '', display_name: '' })

async function handleLogin() {
  if (!loginForm.username.trim() || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(loginForm.username.trim(), loginForm.password)
    router.push('/')
  } catch {
    // interceptor handles display
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const u = regForm.username.trim()
  if (!u || u.length < 2) {
    ElMessage.warning('用户名至少2个字符')
    return
  }
  if (!regForm.password || regForm.password.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  if (regForm.password !== regForm.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    await authStore.register(u, regForm.password, regForm.display_name.trim())
    ElMessage.success('注册成功')
    router.push('/')
  } catch {
    // interceptor handles display
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #1d2b3a 0%, #2d4a6f 50%, #1d2b3a 100%);
}
.login-card {
  width: 420px; padding: 36px 32px; background: #fff;
  border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.login-header { text-align: center; margin-bottom: 8px; }
.login-icon { font-size: 36px; display: block; margin-bottom: 8px; }
.login-header h2 { margin: 0 0 4px; color: #303133; font-size: 22px; }
.subtitle { margin: 0; color: #909399; font-size: 13px; }
.submit-btn { width: 100%; border-radius: 8px; height: 40px; font-size: 15px; }
</style>

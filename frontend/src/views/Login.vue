<script setup lang="ts">
import { ref } from 'vue'
import LoginForm from '@/components/AccountForm/LoginForm.vue'
import RegisterForm from '@/components/AccountForm/RegisterForm.vue'
import ResetPasswordForm from '@/components/AccountForm/ResetPasswordForm.vue'

defineOptions({
  name: 'Login',
})

const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()

const redirect = ref(route.query.redirect?.toString() ?? settingsStore.settings.home.fullPath)
const account = ref<string>()
const formType = ref<'login' | 'register' | 'resetPassword'>('login')
</script>

<template>
  <div class="login-page">
    <div class="login-page__background" />
    <div class="login-page__shell">
      <section class="login-page__brand">
        <img src="/brand-mark.svg" alt="公文写作系统" class="login-page__logo">
        <div class="login-page__brand-copy">
          <p class="login-page__eyebrow">
            写作工作台
          </p>
          <h1 class="login-page__title">
            公文写作系统
          </h1>
          <p class="login-page__description">
            统一管理账户、权限、素材、书籍学习与会话式写作工作流。
          </p>
        </div>
        <img src="@/assets/images/login-banner.png" alt="登录插图" class="login-page__illustration">
      </section>

      <section class="login-page__form-panel">
        <Transition name="fade" mode="out-in">
          <LoginForm
            v-if="formType === 'login'"
            :account="account"
            @on-login="router.push(redirect)"
            @on-register="(value) => { formType = 'register'; account = value }"
            @on-reset-password="(value) => { formType = 'resetPassword'; account = value }"
          />
          <RegisterForm
            v-else-if="formType === 'register'"
            :account="account"
            @on-register="(value) => { formType = 'login'; account = value }"
            @on-login="formType = 'login'"
          />
          <ResetPasswordForm
            v-else
            :account="account"
            @on-reset-password="(value) => { formType = 'login'; account = value }"
            @on-login="formType = 'login'"
          />
        </Transition>
      </section>
    </div>
    <FaCopyright class="login-page__copyright" />
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px;
  overflow: hidden;
  background: var(--w-login-page-bg);
}

.login-page__background {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, var(--w-login-page-glow-1), transparent 35%),
    radial-gradient(circle at bottom right, var(--w-login-page-glow-2), transparent 32%),
    linear-gradient(180deg, var(--w-login-page-gradient-start) 0%, var(--w-login-page-gradient-end) 100%);
}

.login-page__shell {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(320px, 1.1fr) minmax(360px, 0.9fr);
  width: min(1180px, 100%);
  overflow: hidden;
  background: var(--w-login-shell-bg);
  border: 1px solid var(--w-login-shell-border);
  border-radius: 24px;
  box-shadow: var(--w-login-shell-shadow);
}

.login-page__brand {
  display: flex;
  flex-direction: column;
  gap: 28px;
  justify-content: space-between;
  padding: 32px;
  color: var(--w-login-brand-text);
  background: var(--w-login-brand-bg);
}

.login-page__logo {
  width: 44px;
  height: 44px;
}

.login-page__eyebrow {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--w-login-brand-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.login-page__title {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.15;
}

.login-page__description {
  max-width: 440px;
  margin: 16px 0 0;
  font-size: 15px;
  line-height: 1.8;
  color: var(--w-login-brand-secondary);
}

.login-page__illustration {
  align-self: center;
  width: min(100%, 520px);
}

.login-page__form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: var(--w-login-panel-bg);
}

.login-page__copyright {
  position: absolute;
  bottom: 0;
  z-index: 1;
  width: 100%;
  padding: 16px 24px;
  margin: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 960px) {
  .login-page {
    padding: 16px;
  }

  .login-page__shell {
    grid-template-columns: 1fr;
  }

  .login-page__brand,
  .login-page__form-panel {
    padding: 24px;
  }

  .login-page__illustration {
    max-width: 360px;
  }
}
</style>

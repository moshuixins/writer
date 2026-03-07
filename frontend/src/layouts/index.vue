<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { businessNavGroups } from './navigation'

defineOptions({
  name: 'Layout',
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { auth } = useAuth()

const mobileMenuOpen = ref(false)

const visibleGroups = computed(() => {
  return businessNavGroups
    .map(group => ({
      ...group,
      items: group.items.filter(item => auth(item.auth ?? '')),
    }))
    .filter(group => group.items.length > 0)
})

const currentNavItem = computed(() => {
  return visibleGroups.value
    .flatMap(group => group.items.map(item => ({ ...item, groupTitle: group.title })))
    .find(item => route.path === item.path)
})

const currentSectionTitle = computed(() => currentNavItem.value?.groupTitle || '工作台')
const currentRouteTitle = computed(() => {
  if (typeof route.meta.title === 'string' && route.meta.title) {
    return route.meta.title
  }
  return currentNavItem.value?.title || '页面信息'
})

function isActive(path: string) {
  return route.path === path
}

async function go(path: string) {
  mobileMenuOpen.value = false
  if (route.path !== path) {
    await router.push(path)
  }
}

watch(() => route.fullPath, () => {
  mobileMenuOpen.value = false
})
</script>

<template>
  <div class="app-shell">
    <div v-if="mobileMenuOpen" class="app-shell__mask" @click="mobileMenuOpen = false" />

    <aside class="app-shell__sidebar" :class="{ 'is-open': mobileMenuOpen }">
      <div class="app-shell__brand">
        <div class="app-shell__brand-mark">
          W
        </div>
        <div class="app-shell__brand-text">
          <strong>公文写作系统</strong>
          <span>写作工作区与管理后台</span>
        </div>
      </div>

      <nav class="app-shell__nav">
        <section v-for="group in visibleGroups" :key="group.key" class="app-shell__nav-group">
          <div class="app-shell__nav-group-title">
            {{ group.title }}
          </div>
          <button
            v-for="item in group.items"
            :key="item.key"
            class="app-shell__nav-item"
            :class="{ 'is-active': isActive(item.path) }"
            type="button"
            @click="go(item.path)"
          >
            <FaIcon :name="item.icon" class="app-shell__nav-icon" />
            <span>{{ item.title }}</span>
          </button>
        </section>
      </nav>

      <div class="app-shell__sidebar-foot">
        <div class="app-shell__account-card">
          <div class="app-shell__account-label">
            当前账户
          </div>
          <div class="app-shell__account-name">
            {{ userStore.account || '未命名账户' }}
          </div>
        </div>
      </div>
    </aside>

    <div class="app-shell__main">
      <header class="app-shell__topbar">
        <div class="app-shell__topbar-main">
          <button class="app-shell__menu-trigger" type="button" @click="mobileMenuOpen = true">
            <FaIcon name="i-ep:menu" />
          </button>
          <div class="app-shell__topbar-title-wrap">
            <div class="app-shell__topbar-section">
              {{ currentSectionTitle }}
            </div>
            <h1 class="app-shell__topbar-title">
              {{ currentRouteTitle }}
            </h1>
          </div>
        </div>
        <div class="app-shell__topbar-actions">
          <div class="app-shell__topbar-summary">
            <span>{{ userStore.user?.display_name || userStore.account || '未登录用户' }}</span>
            <span>{{ userStore.user?.department || '未设置部门' }}</span>
          </div>
          <AppUserMenu />
        </div>
      </header>

      <main class="app-shell__canvas">
        <RouterView v-slot="{ Component, route: currentRoute }">
          <Transition name="canvas-fade" mode="out-in">
            <component :is="Component" :key="currentRoute.fullPath" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100%;
  color: var(--w-text-primary);
  background: var(--w-shell-bg);
}

.app-shell__mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: var(--w-overlay);
}

.app-shell__sidebar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: var(--w-sidebar-width);
  min-height: 100vh;
  padding: 20px 16px 16px;
  color: var(--w-shell-sidebar-text);
  background: radial-gradient(circle at top, var(--w-shell-sidebar-glow) 0%, transparent 32%), var(--w-shell-sidebar-bg);
}

.app-shell__brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 10px 14px;
  border-bottom: 1px solid var(--w-shell-sidebar-border);
}

.app-shell__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  font-size: 18px;
  font-weight: 800;
  color: var(--w-shell-sidebar-active-text);
  background: var(--w-shell-sidebar-active-bg);
  border-radius: 12px;
}

.app-shell__brand-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.app-shell__brand-text strong {
  font-size: 14px;
  line-height: 1.3;
}

.app-shell__brand-text span {
  font-size: 12px;
  color: var(--w-shell-sidebar-muted);
}

.app-shell__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 18px;
}

.app-shell__nav-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.app-shell__nav-group-title {
  padding: 0 10px;
  font-size: 11px;
  font-weight: 700;
  color: var(--w-shell-sidebar-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.app-shell__nav-item {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 12px 14px;
  color: inherit;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 14px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.app-shell__nav-item:hover {
  background: var(--w-shell-sidebar-card);
  border-color: var(--w-shell-sidebar-border);
  transform: translateX(2px);
}

.app-shell__nav-item.is-active {
  color: var(--w-shell-sidebar-active-text);
  background: var(--w-shell-sidebar-active-bg);
}

.app-shell__nav-icon {
  font-size: 18px;
}

.app-shell__sidebar-foot {
  padding-top: 6px;
}

.app-shell__account-card {
  padding: 14px;
  background: var(--w-shell-sidebar-card);
  border: 1px solid var(--w-shell-sidebar-border);
  border-radius: 16px;
}

.app-shell__account-label {
  font-size: 11px;
  color: var(--w-shell-sidebar-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.app-shell__account-name {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
}

.app-shell__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.app-shell__topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  min-height: var(--w-topbar-height);
  padding: 16px 24px;
  background: var(--w-shell-topbar-bg);
  border-bottom: 1px solid var(--w-shell-topbar-border);
}

@supports (backdrop-filter: blur(12px)) {
  .app-shell__topbar {
    backdrop-filter: blur(12px);
  }
}

.app-shell__topbar-main,
.app-shell__topbar-actions {
  display: flex;
  gap: 14px;
  align-items: center;
}

.app-shell__topbar-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-shell__topbar-section {
  font-size: 11px;
  font-weight: 700;
  color: var(--w-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.app-shell__topbar-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.25;
}

.app-shell__topbar-summary {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-end;
  font-size: 12px;
  color: var(--w-text-secondary);
}

.app-shell__menu-trigger {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--w-text-primary);
  background: var(--w-color-white);
  border: 1px solid var(--w-divider);
  border-radius: 12px;
}

.app-shell__canvas {
  flex: 1;
  min-width: 0;
  background: var(--w-shell-canvas-bg);
}

.canvas-fade-enter-active,
.canvas-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.canvas-fade-enter-from,
.canvas-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 1024px) {
  .app-shell {
    min-height: 100vh;
  }

  .app-shell__sidebar {
    position: fixed;
    left: 0;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }

  .app-shell__sidebar.is-open {
    transform: translateX(0);
  }

  .app-shell__menu-trigger {
    display: inline-flex;
  }
}

@media (max-width: 768px) {
  .app-shell__topbar {
    padding: 14px 16px;
  }

  .app-shell__topbar-title {
    font-size: 18px;
  }

  .app-shell__topbar-summary {
    display: none;
  }
}
</style>

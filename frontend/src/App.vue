<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { ua } from '@/utils/ua'
import Provider from './ui/provider/index.vue'

const route = useRoute()

const settingsStore = useSettingsStore()
const { auth } = useAuth()

document.body.setAttribute('data-os', ua.getOS().name || '')

const isAuth = computed(() => {
  return route.matched.every((item) => {
    return auth(item.meta.auth ?? '')
  })
})

function syncViewportMode() {
  settingsStore.setMode(document.documentElement.clientWidth)
}

watch([
  () => settingsStore.settings.app.enableDynamicTitle,
  () => settingsStore.title,
], () => {
  const appTitle = import.meta.env.VITE_APP_TITLE || '公文写作系统'
  if (settingsStore.settings.app.enableDynamicTitle && settingsStore.title) {
    const title = typeof settingsStore.title === 'function' ? settingsStore.title() : settingsStore.title
    document.title = `${title} - ${appTitle}`
    return
  }
  document.title = appTitle
}, {
  immediate: true,
  deep: true,
})

onMounted(() => {
  syncViewportMode()
  window.addEventListener('resize', syncViewportMode)
})

onUnmounted(() => {
  window.removeEventListener('resize', syncViewportMode)
})
</script>

<template>
  <Provider>
    <RouterView v-slot="{ Component }">
      <component :is="Component" v-if="isAuth" />
      <FaNotAllowed v-else />
    </RouterView>
    <FaBackToTop />
    <FaToast />
    <FaNotification />
    <FaSystemInfo />
  </Provider>
</template>

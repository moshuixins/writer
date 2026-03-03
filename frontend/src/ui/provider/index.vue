<script setup lang="ts">
import zhCN from 'element-plus/es/locale/lang/zh-cn'

const settingsStore = useSettingsStore()

// 跟随框架主题
const isSupprotColorMix = CSS.supports('color', 'color-mix(in srgb, #fff, #000)')
if (isSupprotColorMix) {
  document.body.style.setProperty('--el-bg-color', 'hsl(var(--background))')
  document.body.style.setProperty('--el-color-primary', 'var(--w-btn-primary-bg)')
  document.body.style.setProperty('--el-color-white', 'var(--w-color-white)')
  document.body.style.setProperty('--el-color-black', 'var(--w-color-black)')
  watch(() => settingsStore.currentColorScheme, () => {
    for (let index = 1; index < 10; index++) {
      document.body.style.setProperty(`--el-color-primary-light-${index}`, `color-mix(in srgb, var(--w-btn-primary-bg), #fff ${index * 10}%)`)
      document.body.style.setProperty(`--el-color-primary-dark-${index}`, `color-mix(in srgb, var(--w-btn-primary-bg), #000 ${index * 10}%)`)
    }
  }, {
    immediate: true,
  })
}
</script>

<template>
  <ElConfigProvider :locale="zhCN" :button="{ autoInsertSpace: true }">
    <slot />
  </ElConfigProvider>
</template>

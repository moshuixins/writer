<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  size?: 'large' | 'default' | 'small'
}>(), {
  tone: 'neutral',
  size: 'small',
})

const tagType = computed(() => {
  switch (props.tone) {
    case 'success':
      return 'success'
    case 'warning':
      return 'warning'
    case 'danger':
      return 'danger'
    default:
      return 'info'
  }
})
</script>

<template>
  <el-tag :type="tagType" :size="size" class="status-badge" :class="`status-badge--${tone}`">
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  size?: 'large' | 'default' | 'small'
}>(), {
  tone: 'neutral',
  size: 'small',
})
</script>

<template>
  <span class="status-badge" :class="[`status-badge--${tone}`, size === 'large' ? 'status-badge--large' : '']">
    <span class="status-badge__dot" />
    <span>{{ label }}</span>
  </span>
</template>

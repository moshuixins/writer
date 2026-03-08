<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  tone?: 'neutral' | 'muted' | 'accent' | 'warning'
}>(), {
  tone: 'neutral',
})
</script>

<template>
  <span class="meta-tag" :class="`meta-tag--${tone}`">{{ label }}</span>
</template>

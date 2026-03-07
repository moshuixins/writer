<script setup lang="ts">
withDefaults(defineProps<{
  muted?: boolean
}>(), {
  muted: false,
})
</script>

<template>
  <div class="action-bar" :class="{ 'action-bar--muted': muted }">
    <slot />
  </div>
</template>

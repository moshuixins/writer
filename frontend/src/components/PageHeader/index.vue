<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  subtitle?: string
}>(), {
  subtitle: '',
})
</script>

<template>
  <div class="page-header">
    <div class="page-heading">
      <h2 class="page-title">
        {{ title }}
      </h2>
      <p v-if="subtitle" class="page-subtitle">
        {{ subtitle }}
      </p>
    </div>
    <div v-if="$slots.actions" class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

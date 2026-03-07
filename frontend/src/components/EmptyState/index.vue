<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  title: string
  description?: string
}>(), {
  icon: 'i-ep:document',
  description: '',
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon">
      <FaIcon :name="icon" />
    </div>
    <p class="empty-state__title">
      {{ title }}
    </p>
    <p v-if="description" class="empty-state__description">
      {{ description }}
    </p>
    <slot />
  </div>
</template>

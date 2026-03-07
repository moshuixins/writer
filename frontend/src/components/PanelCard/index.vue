<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  subtitle?: string
}>(), {
  title: '',
  subtitle: '',
})
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template v-if="title || subtitle || $slots.header || $slots.actions" #header>
      <div class="panel-card__header">
        <slot name="header">
          <div class="panel-card__title-wrap">
            <div v-if="title" class="panel-card__title">
              {{ title }}
            </div>
            <div v-if="subtitle" class="panel-card__subtitle">
              {{ subtitle }}
            </div>
          </div>
        </slot>
        <div v-if="$slots.actions" class="panel-card__actions">
          <slot name="actions" />
        </div>
      </div>
    </template>
    <slot />
  </el-card>
</template>

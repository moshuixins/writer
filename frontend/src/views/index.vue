<route lang="yaml">
meta:
  title: 主页
  constant: true
</route>

<script setup lang="ts">
const router = useRouter()
router.replace('/chat')
</script>

<template>
  <div />
</template>

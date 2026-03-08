<script setup lang="ts">
import missingIllustration from '@/assets/icons/404.svg'

const router = useRouter()

const settingsStore = useSettingsStore()

const data = ref({
  inter: Number.NaN,
  countdown: 5,
})

onBeforeRouteLeave(() => {
  data.value.inter && window.clearInterval(data.value.inter)
})

onMounted(() => {
  data.value.inter = window.setInterval(() => {
    data.value.countdown--
    if (data.value.countdown === 0) {
      data.value.inter && window.clearInterval(data.value.inter)
      goBack()
    }
  }, 1000)
})

function goBack() {
  router.push(settingsStore.settings.home.fullPath)
}
</script>

<template>
  <div class="absolute left-[50%] top-[50%] flex flex-col items-center justify-between gap-10 lg-flex-row -translate-x-50% -translate-y-50% lg-gap-12">
    <img :src="missingIllustration" alt="" class="h-auto w-[300px] lg:w-[400px]" aria-hidden="true">
    <div class="flex flex-col gap-4">
      <h1 class="m-0 text-6xl font-sans">
        404
      </h1>
      <div class="mx-0 text-xl text-secondary-foreground/50">
        抱歉，你访问的页面不存在
      </div>
      <div>
        <FaButton @click="goBack">
          {{ data.countdown }} 秒后，返回首页
        </FaButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { toast } from 'vue-sonner'
import apiUser from '@/api/modules/user'
import EditPasswordForm from '@/components/AccountForm/EditPasswordForm.vue'

const userStore = useUserStore()

const active = ref(0)
const savingProfile = ref(false)
const profile = reactive({
  username: '',
  display_name: '',
  department: '',
})

const tabs = ref([
  {
    title: '基本设置',
    description: '账号的基本信息，名称、部门等',
  },
  {
    title: '安全设置',
    description: '定期修改密码可以提高账号安全性',
  },
])

async function loadProfile() {
  try {
    const { data } = await apiUser.getProfile({ skipErrorToast: true })
    Object.assign(profile, {
      username: data?.username || '',
      display_name: data?.display_name || '',
      department: data?.department || '',
    })
  }
  catch {
    ElMessage.error('加载个人资料失败，请稍后重试')
  }
}

async function saveProfile() {
  savingProfile.value = true
  try {
    const { data } = await apiUser.updateProfile(
      {
        display_name: profile.display_name,
        department: profile.department,
      },
      { skipErrorToast: true },
    )
    if (data?.user) {
      localStorage.setItem('user', JSON.stringify(data.user))
      userStore.user = data.user
    }
    toast.success('个人资料已保存')
  }
  catch {
    ElMessage.error('保存失败，请稍后重试')
  }
  finally {
    savingProfile.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<template>
  <div class="min-h-full w-full">
    <div class="fixed right-0 top-0 z-1 flex flex-row overflow-auto border-b border-e bg-background md:(inset-s-0 bottom-0 h-full w-40 flex-col)">
      <div v-for="(tab, index) in tabs" :key="index" class="flex-shrink-0 cursor-pointer px-4 py-3 transition-background-color space-y-2 hover-bg-accent/50" :class="{ 'bg-accent hover-bg-accent!': active === index }" @click="active = index">
        <div class="text-base text-accent-foreground leading-tight">
          {{ tab.title }}
        </div>
        <div class="text-xs text-accent-foreground/50">
          {{ tab.description }}
        </div>
      </div>
    </div>
    <div class="min-h-full flex-col-center p-10 pt-20 md:(ms-40 pt-10)">
      <div v-if="active === 0" class="w-full flex-col-stretch-center">
        <div class="mb-6 space-y-2">
          <h3 class="text-4xl color-[var(--el-text-color-primary)] font-bold">
            个人资料
          </h3>
          <p class="text-sm text-muted-foreground lg:text-base">
            修改显示名称和所属部门信息
          </p>
        </div>
        <form @submit.prevent="saveProfile">
          <div class="pb-6">
            <div class="mb-2 text-sm text-muted-foreground">
              用户名
            </div>
            <FaInput v-model="profile.username" class="w-full" disabled />
          </div>
          <div class="pb-6">
            <div class="mb-2 text-sm text-muted-foreground">
              显示名称
            </div>
            <FaInput v-model="profile.display_name" class="w-full" placeholder="请输入显示名称" />
          </div>
          <div class="pb-6">
            <div class="mb-2 text-sm text-muted-foreground">
              所属部门
            </div>
            <FaInput v-model="profile.department" class="w-full" placeholder="如：交管支队" />
          </div>
          <FaButton :loading="savingProfile" size="lg" class="mt-8 w-full" type="submit">
            保存
          </FaButton>
        </form>
      </div>
      <EditPasswordForm v-if="active === 1" />
    </div>
  </div>
</template>

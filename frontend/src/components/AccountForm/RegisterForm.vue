<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { ElMessage } from 'element-plus'
import { useForm } from 'vee-validate'
import * as z from 'zod'
import { useUserStore } from '@/store/modules/user'
import { FormControl, FormDescription, FormField, FormItem, FormMessage } from '@/ui/shadcn/ui/form'

defineOptions({
  name: 'RegisterForm',
})

const props = defineProps<{
  account?: string
}>()

const emits = defineEmits<{
  onLogin: [account?: string]
  onRegister: [account?: string]
}>()

const userStore = useUserStore()
const loading = ref(false)

const form = useForm({
  validationSchema: toTypedSchema(
    z.object({
      invite_code: z.string().min(1, '请输入邀请码'),
      account: z.string().min(1, '请输入用户名'),
      password: z.string().min(1, '请输入密码').min(6, '密码长度为6到18位').max(18, '密码长度为6到18位'),
      checkPassword: z.string().min(1, '请再次输入密码'),
    }).refine(data => data.password === data.checkPassword, {
      message: '两次输入的密码不一致',
      path: ['checkPassword'],
    }),
  ),
  initialValues: {
    account: props.account ?? '',
    invite_code: '',
    password: '',
    checkPassword: '',
  },
})
const onSubmit = form.handleSubmit(async (values) => {
  loading.value = true
  try {
    await userStore.register({
      username: values.account,
      password: values.password,
      invite_code: values.invite_code,
    })
    ElMessage.success('注册成功，请登录')
    emits('onRegister', values.account)
  }
  catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注册失败')
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-500px w-full flex-col-stretch-center p-12">
    <form @submit="onSubmit">
      <div class="mb-8 space-y-2">
        <h3 class="text-4xl color-[var(--el-text-color-primary)] font-bold">
          创建账号
        </h3>
        <p class="text-sm text-muted-foreground lg:text-base">
          注册后即可使用公文写作助手
        </p>
      </div>
      <FormField v-slot="{ componentField, errors }" name="account">
        <FormItem class="relative pb-6 space-y-0">
          <FormControl>
            <FaInput type="text" placeholder="请输入用户名" class="w-full" :class="errors.length && 'border-destructive'" v-bind="componentField" />
          </FormControl>
          <Transition enter-active-class="transition-opacity" enter-from-class="opacity-0" leave-active-class="transition-opacity" leave-to-class="opacity-0">
            <FormMessage class="absolute bottom-1 text-xs" />
          </Transition>
        </FormItem>
      </FormField>
      <FormField v-slot="{ componentField, errors }" name="invite_code">
        <FormItem class="relative pb-6 space-y-0">
          <FormControl>
            <FaInput type="text" placeholder="请输入邀请码" class="w-full" :class="errors.length && 'border-destructive'" v-bind="componentField" />
          </FormControl>
          <Transition enter-active-class="transition-opacity" enter-from-class="opacity-0" leave-active-class="transition-opacity" leave-to-class="opacity-0">
            <FormMessage class="absolute bottom-1 text-xs" />
          </Transition>
        </FormItem>
      </FormField>
      <FormField v-slot="{ componentField, value, errors }" name="password">
        <FormItem class="relative pb-6 space-y-0">
          <FormControl>
            <FaInput type="password" placeholder="请输入密码" class="w-full" :class="errors.length && 'border-destructive'" v-bind="componentField" />
          </FormControl>
          <FormDescription>
            <FaPasswordStrength :password="value" class="mt-2" />
          </FormDescription>
          <Transition enter-active-class="transition-opacity" enter-from-class="opacity-0" leave-active-class="transition-opacity" leave-to-class="opacity-0">
            <FormMessage class="absolute bottom-1 text-xs" />
          </Transition>
        </FormItem>
      </FormField>
      <FormField v-slot="{ componentField, errors }" name="checkPassword">
        <FormItem class="relative pb-6 space-y-0">
          <FormControl>
            <FaInput type="password" placeholder="请再次输入密码" class="w-full" :class="errors.length && 'border-destructive'" v-bind="componentField" />
          </FormControl>
          <Transition enter-active-class="transition-opacity" enter-from-class="opacity-0" leave-active-class="transition-opacity" leave-to-class="opacity-0">
            <FormMessage class="absolute bottom-1 text-xs" />
          </Transition>
        </FormItem>
      </FormField>
      <FaButton :loading="loading" size="lg" class="mt-4 w-full" type="submit">
        注册
      </FaButton>
      <div class="mt-4 flex-center gap-2 text-sm">
        <span class="text-secondary-foreground op-50">已经有帐号?</span>
        <FaButton variant="link" class="h-auto p-0" @click="emits('onLogin', form.values.account)">
          去登录
        </FaButton>
      </div>
    </form>
  </div>
</template>

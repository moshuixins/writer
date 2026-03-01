<template>
  <div class="settings-page">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2 class="page-title">写作偏好</h2>
        <p class="page-subtitle">设置单位署名、语气和常用用词，AI 生成时将自动参考</p>
      </div>
    </div>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span class="card-title">写作偏好</span>
        <span class="card-desc">AI 会在生成公文时自动应用这些偏好</span>
      </template>
      <el-form label-width="120px" style="max-width: 560px">
        <el-form-item label="单位名称">
          <el-input v-model="prefs.signature_org" placeholder="如：XX市公安局交通管理支队" />
        </el-form-item>
        <el-form-item label="默认语气">
          <el-select v-model="prefs.default_tone">
            <el-option label="正式" value="formal" />
            <el-option label="半正式" value="semi-formal" />
          </el-select>
        </el-form-item>
        <el-form-item label="常用主送机关">
          <el-input v-model="prefs.default_recipients" placeholder="如：各大队、机关各科室" />
        </el-form-item>
        <el-form-item label="避免用词">
          <el-input v-model="prefs.avoid_phrases" placeholder="逗号分隔，如：切实,进一步" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingPrefs" @click="savePrefs">保存偏好</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import apiPreferences from '@/api/modules/preferences'
import type { Preferences } from '@/types/writer'

const savingPrefs = ref(false)

const prefs = reactive<Preferences>({
  signature_org: '',
  default_tone: 'formal',
  default_recipients: '',
  avoid_phrases: '',
})

async function loadPrefs() {
  try {
    const { data } = await apiPreferences.get({ skipErrorToast: true })
    Object.assign(prefs, data)
  }
  catch {
    ElMessage.error('加载偏好失败，请刷新重试')
  }
}

async function savePrefs() {
  savingPrefs.value = true
  try {
    await apiPreferences.save({ ...prefs }, { skipErrorToast: true })
    ElMessage.success('偏好已保存')
  }
  catch {
    ElMessage.error('保存失败，请稍后重试')
  }
  finally {
    savingPrefs.value = false
  }
}

onMounted(() => {
  loadPrefs()
})
</script>

<style scoped>
.settings-page {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.settings-card :deep(.el-card__header) {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.card-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .settings-page {
    padding: 16px;
  }
}
</style>

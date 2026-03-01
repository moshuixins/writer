<template>
  <div class="settings-page">
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

const savingPrefs = ref(false)

const prefs = reactive({
  signature_org: '',
  default_tone: 'formal',
  default_recipients: '',
  avoid_phrases: '',
})

async function loadPrefs() {
  try {
    const { data } = await apiPreferences.get()
    Object.assign(prefs, data)
  }
  catch {}
}

async function savePrefs() {
  savingPrefs.value = true
  try {
    await apiPreferences.save({ ...prefs })
    ElMessage.success('偏好已保存')
  }
  catch {}
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
</style>

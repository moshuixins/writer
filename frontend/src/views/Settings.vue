<template>
  <div class="settings-page">
    <h2>偏好设置</h2>
    <p>设置您的写作偏好，AI会在生成公文时自动应用这些偏好。</p>

    <el-form label-width="140px" style="max-width: 600px; margin-top: 24px">
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
        <el-button type="primary" @click="saveAll" :loading="saving">保存设置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const saving = ref(false)

const prefs = reactive({
  signature_org: '',
  default_tone: 'formal',
  default_recipients: '',
  avoid_phrases: '',
})

async function loadPrefs() {
  try {
    const { data } = await api.get('/preferences')
    Object.assign(prefs, data)
  } catch {
    // interceptor handles error display
  }
}

async function saveAll() {
  saving.value = true
  try {
    await api.put('/preferences/batch', { ...prefs })
    ElMessage.success('设置已保存')
  } catch {
    // interceptor handles error display
  } finally {
    saving.value = false
  }
}

onMounted(loadPrefs)
</script>

<style scoped>
.settings-page { padding: 20px; }
</style>


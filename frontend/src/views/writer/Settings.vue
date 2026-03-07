<script setup lang="ts">
import type { Preferences } from '@/types/writer'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import apiPreferences from '@/api/modules/preferences'
import PageHeader from '@/components/PageHeader/index.vue'
import PageShell from '@/components/PageShell/index.vue'
import PanelCard from '@/components/PanelCard/index.vue'

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
  void loadPrefs()
})
</script>

<template>
  <PageShell class="page-shell--compact">
    <PageHeader
      title="写作偏好"
      subtitle="设置单位署名、默认语气和常用收文对象，生成时会自动参考这些偏好。"
    >
      <template #actions>
        <el-button type="primary" :loading="savingPrefs" @click="savePrefs">
          保存偏好
        </el-button>
      </template>
    </PageHeader>

    <div class="settings-grid">
      <PanelCard
        title="默认写作设置"
        subtitle="这部分会直接参与生成提示，建议按实际单位和常用行文习惯维护。"
      >
        <el-form label-position="top" class="preferences-form">
          <el-form-item label="单位名称">
            <el-input v-model="prefs.signature_org" placeholder="如：XX市公安局交通管理支队" />
          </el-form-item>
          <el-form-item label="默认语气">
            <el-select v-model="prefs.default_tone" class="field-select">
              <el-option label="正式" value="formal" />
              <el-option label="半正式" value="semi-formal" />
            </el-select>
          </el-form-item>
          <el-form-item label="常用主送机关">
            <el-input v-model="prefs.default_recipients" placeholder="如：各大队、机关各科室" />
          </el-form-item>
          <el-form-item label="避免用词">
            <el-input
              v-model="prefs.avoid_phrases"
              type="textarea"
              :rows="4"
              placeholder="使用逗号分隔，如：切实、进一步、务必"
            />
          </el-form-item>
        </el-form>
      </PanelCard>

      <PanelCard
        title="使用建议"
        subtitle="偏好越稳定，生成结果越接近你的单位文风。"
      >
        <ul class="tips-list">
          <li>单位名称会优先写入落款与正文指代，建议保持正式全称。</li>
          <li>常用主送机关适合填写稳定收文对象，减少每次重复说明。</li>
          <li>避免用词可录入本单位明确不建议出现的套话或表述习惯。</li>
          <li>偏好只影响生成倾向，不会修改你在编辑器中的既有内容。</li>
        </ul>
      </PanelCard>
    </div>
  </PageShell>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 16px;
}

.preferences-form {
  max-width: 640px;
}

.field-select {
  width: 100%;
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 18px;
  margin: 0;
  line-height: 1.7;
  color: var(--w-text-secondary);
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>

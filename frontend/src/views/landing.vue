<script setup lang="ts">
import type { ChatSession } from '@/types/writer'
import apiChat from '@/api/modules/chat'
import { applySeoMeta, resetSeoMeta } from '@/utils/seo'

interface LandingMetric {
  value: string
  label: string
  detail: string
}

interface LandingFeaturePanel {
  eyebrow: string
  title: string
  description: string
  icon: string
}

interface LandingStep {
  index: string
  title: string
  description: string
  result: string
}

interface LandingDemoScene {
  id: 'conversation' | 'knowledge' | 'governance'
  label: string
  title: string
  description: string
  highlight: string
  bullets: string[]
}

const LAST_SESSION_STORAGE_KEY = 'writer:last-session-id'

const router = useRouter()
const userStore = useUserStore()

const loadingEntry = ref(false)
const sessions = ref<ChatSession[]>([])
const activeDemoId = ref<LandingDemoScene['id']>('conversation')

const sectionLinks = [
  { label: '产品演示', selector: '#demo' },
  { label: '能力结构', selector: '#structure' },
  { label: '进入路径', selector: '#workflow' },
]

const heroMetrics: LandingMetric[] = [
  { value: '79+1', label: '规范文种体系', detail: '覆盖 79 个子类与“其他”兜底。' },
  { value: '11', label: '大类分组管理', detail: '前后端文种选择与筛选统一收口。' },
  { value: '20', label: '最近会话上下文', detail: '会话上下文保留最近 20 条，聚焦当前任务。' },
  { value: 'RBAC', label: '账户与权限隔离', detail: '素材、记忆与管理能力按账户边界收口。' },
]

const featurePanels: LandingFeaturePanel[] = [
  {
    eyebrow: '会话写作',
    title: '先进入会话列表，再进入工作台，入口层级更稳定',
    description: '把多任务切换、续写和回看统一放到会话入口层，避免一进入系统就被复杂工作台打断。',
    icon: 'i-ep:chat-dot-round',
  },
  {
    eyebrow: '知识增强',
    title: '素材、书籍与风格规则进入同一条增强链路',
    description: '素材不再只是附件仓库，书籍也不是单独功能区，而是统一转成可检索、可提炼、可写作调用的知识资产。',
    icon: 'i-ep:reading',
  },
  {
    eyebrow: '正式排版',
    title: '对话、工作流、正文编辑同屏协作，保持公文语境',
    description: '编辑器保留正式公文排版，AI 区负责结构建议和改写，避免通用聊天产品式的上下文噪音。',
    icon: 'i-ep:edit-pen',
  },
  {
    eyebrow: '后台治理',
    title: '账户、角色、权限、邀请码与导入任务都可在前端运维',
    description: '把 RBAC、导入状态、错误追踪和账户资源管理放到同一套后台表达里，支持组织化使用。',
    icon: 'i-ep:key',
  },
]

const workflowSteps: LandingStep[] = [
  {
    index: '01',
    title: '按事项建立会话',
    description: '从会话列表进入工作台，而不是从空白编辑器开始，先把任务边界和文种固定下来。',
    result: '结果：入口清晰，续写路径稳定。',
  },
  {
    index: '02',
    title: '汇聚账户级知识',
    description: '素材上传、书籍学习、风格规则与会话记忆形成同一底座，为生成前检索和风格吸收服务。',
    result: '结果：不靠单次 prompt 硬凑上下文。',
  },
  {
    index: '03',
    title: 'AI 生成与正文编辑并行',
    description: '工作流步骤、消息流和正文面板同时可见，适合逐段起草、改写、引用和导出。',
    result: '结果：把生成过程变成可控工作流。',
  },
  {
    index: '04',
    title: '管理员持续治理',
    description: '通过账户、角色、权限和任务状态管理，把写作系统从个人工具平滑过渡到团队系统。',
    result: '结果：上线后可维护、可审计、可扩展。',
  },
]

const demoScenes: LandingDemoScene[] = [
  {
    id: 'conversation',
    label: '写作工作台',
    title: '会话入口层先于工作台，真正符合持续写作的工作节奏',
    description: '从会话列表进入工作台，可以先决定任务，再进入正文与 AI 协作界面。相比一打开就是聊天区，这样的组织方式更适合正式写作。',
    highlight: '最近会话可直接续写',
    bullets: ['会话入口与正文编辑解耦，切换任务更稳。', '工作流步骤、对话气泡、正文纸面三者主次分明。', '登录后优先回到最近任务，而不是再次寻找入口。'],
  },
  {
    id: 'knowledge',
    label: '知识增强',
    title: '把素材、书籍与风格规则压进一套知识增强工作台',
    description: '知识区不是文件仓库，而是被持续解析、提炼和调用的系统资产。它支撑的不只是检索，更是结构和写法层面的增强。',
    highlight: 'OCR、摘要、风格规则形成闭环',
    bullets: ['素材上传后自动完成分类、摘要、关键词和风格分析。', '书籍学习支持 EPUB、文本 PDF 与扫描 PDF OCR。', '风格规则优先补结构、逻辑、措辞和数据表达方式。'],
  },
  {
    id: 'governance',
    label: '治理后台',
    title: '后台不是附属页面，而是系统可信边界的一部分',
    description: '当写作进入团队使用阶段，账户、角色、邀请码、导入任务和错误追踪必须出现在同一套后台逻辑下。',
    highlight: '资源按账户隔离，权限按角色落地',
    bullets: ['管理员页面统一维护账户、用户、角色和权限。', '邀请码和权限矩阵从一开始就具备正式后台表达。', '错误、导入与 OCR 统计可观测，便于长期运维。'],
  },
]

const activeDemo = computed(() => demoScenes.find(scene => scene.id === activeDemoId.value) || demoScenes[0])
const accountSnapshot = computed(() => userStore.isLogin ? userStore.account : '访客模式')

const landingSeoMeta = {
  title: '正式公文写作平台 - 公文写作系统',
  description: '面向正式公文场景的团队级智能写作平台，统一会话写作、素材治理、书籍学习、风格增强与权限管理，支持从落地页进入正式工作区。',
  keywords: ['公文写作系统', '正式公文', '公文写作', '智能写作', '书籍学习', '素材治理', '角色权限'],
  path: '/',
  image: '/og-cover.png',
}

onMounted(() => {
  applySeoMeta(landingSeoMeta)
})

onBeforeUnmount(() => {
  resetSeoMeta()
})

function canUseSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
}

function readStoredSessionId() {
  if (!canUseSessionStorage()) {
    return null
  }

  const raw = window.sessionStorage.getItem(LAST_SESSION_STORAGE_KEY)
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

async function loadEntrySessions() {
  if (!userStore.isLogin) {
    sessions.value = []
    return
  }

  loadingEntry.value = true
  try {
    const { data } = await apiChat.getSessions()
    sessions.value = [...data].sort((left, right) => {
      const rightTime = Date.parse(right.created_at || '')
      const leftTime = Date.parse(left.created_at || '')
      return rightTime - leftTime
    })
  }
  catch {
    sessions.value = []
  }
  finally {
    loadingEntry.value = false
  }
}

watch(() => userStore.isLogin, (isLogin) => {
  if (isLogin) {
    void loadEntrySessions()
    return
  }
  sessions.value = []
}, { immediate: true })

const entrySession = computed(() => {
  const storedId = readStoredSessionId()
  if (storedId) {
    const storedSession = sessions.value.find(session => Number(session.id) === storedId)
    if (storedSession) {
      return storedSession
    }
  }
  return sessions.value[0] || null
})

const demoSessionTitle = computed(() => entrySession.value?.title || '关于春季安全检查工作的通知')
const demoSessionType = computed(() => entrySession.value?.doc_type || '通知')

const entryStateLabel = computed(() => {
  if (!userStore.isLogin) {
    return '公开入口'
  }
  if (loadingEntry.value) {
    return '工作区入口'
  }
  if (entrySession.value) {
    return '最近会话直达'
  }
  return '首个任务入口'
})

const entryStateTitle = computed(() => {
  if (!userStore.isLogin) {
    return '先看演示，再登录进入正式工作区'
  }
  if (loadingEntry.value) {
    return '正在读取当前账户的会话入口'
  }
  if (entrySession.value) {
    return entrySession.value.title
  }
  return '当前账户还没有会话，可先进入会话列表创建首个任务'
})

const entryStateDescription = computed(() => {
  if (!userStore.isLogin) {
    return '落地页负责讲清系统结构和能力边界。登录后再进入会话、素材、书籍学习和管理后台。'
  }
  if (loadingEntry.value) {
    return '系统正在判断是否存在最近会话，并准备最短进入路径。'
  }
  if (entrySession.value) {
    return `当前账户共有 ${sessions.value.length} 个会话，主按钮会直接带你回到最近一次工作。`
  }
  return '当前账户暂无写作会话，主按钮会先进入会话列表，让你从真实任务开始。'
})

const primaryActionLabel = computed(() => {
  if (!userStore.isLogin) {
    return '登录系统'
  }
  if (loadingEntry.value) {
    return '打开工作区'
  }
  if (entrySession.value) {
    return '继续最近会话'
  }
  return '创建首个会话'
})

const secondaryActionLabel = computed(() => {
  if (!userStore.isLogin) {
    return '查看产品演示'
  }
  if (loadingEntry.value || sessions.value.length > 0) {
    return '查看全部会话'
  }
  return '查看产品演示'
})

function openPrimaryAction() {
  if (!userStore.isLogin) {
    void router.push('/login')
    return
  }

  if (entrySession.value) {
    void router.push({
      name: 'writerWorkspace',
      params: { sessionId: entrySession.value.id },
    })
    return
  }

  void router.push('/chat')
}

function openSecondaryAction() {
  if (userStore.isLogin && (loadingEntry.value || sessions.value.length > 0)) {
    void router.push('/chat')
    return
  }

  scrollToSection('#demo')
}

function scrollToSection(selector: string) {
  document.querySelector<HTMLElement>(selector)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}
</script>

<template>
  <div class="landing-page">
    <div class="landing-page__grain" />
    <div class="landing-page__halo landing-page__halo--top" />
    <div class="landing-page__halo landing-page__halo--side" />

    <header class="landing-topbar">
      <button class="landing-brand" type="button" @click="scrollToSection('#hero')">
        <img src="/brand-mark.svg" alt="公文写作系统" class="landing-brand__mark">
        <span class="landing-brand__copy">
          <strong>公文写作系统</strong>
          <small>正式、公务化、可治理的写作平台</small>
        </span>
      </button>

      <nav class="landing-topbar__nav">
        <button v-for="link in sectionLinks" :key="link.selector" type="button" @click="scrollToSection(link.selector)">
          {{ link.label }}
        </button>
      </nav>

      <div class="landing-topbar__actions">
        <el-button @click="openSecondaryAction">
          {{ secondaryActionLabel }}
        </el-button>
        <el-button type="primary" @click="openPrimaryAction">
          {{ primaryActionLabel }}
        </el-button>
      </div>
    </header>

    <main class="landing-main">
      <section id="hero" class="hero">
        <div class="hero__main">
          <div class="section-kicker">
            为正式公文生产而设计
          </div>
          <h1 class="hero__title">
            把写作、知识增强与权限治理压缩进一套真正可落地的公文系统
          </h1>
          <p class="hero__description">
            这不是把通用聊天框换成公文文案，而是用会话入口、知识工作台、正式排版和治理后台重建完整的公文生产路径。它适合持续改稿、多人协作、长期积累和组织化上线。
          </p>

          <div class="hero__actions">
            <el-button type="primary" size="large" @click="openPrimaryAction">
              {{ primaryActionLabel }}
            </el-button>
            <el-button size="large" @click="openSecondaryAction">
              {{ secondaryActionLabel }}
            </el-button>
          </div>

          <div class="hero__metrics">
            <article v-for="metric in heroMetrics" :key="metric.label" class="hero-metric">
              <span class="hero-metric__label">{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <p>{{ metric.detail }}</p>
            </article>
          </div>
        </div>

        <div class="hero__rail">
          <article class="hero-card hero-card--entry">
            <div class="hero-card__eyebrow">
              {{ entryStateLabel }}
            </div>
            <strong>{{ entryStateTitle }}</strong>
            <p>{{ entryStateDescription }}</p>
            <div class="hero-card__meta-grid">
              <div>
                <span>当前账户</span>
                <strong>{{ accountSnapshot }}</strong>
              </div>
              <div>
                <span>当前会话</span>
                <strong>{{ loadingEntry ? '读取中' : sessions.length }}</strong>
              </div>
            </div>
          </article>

          <article class="hero-card hero-card--studio">
            <div class="hero-card__eyebrow">
              工作台样片
            </div>
            <div class="hero-studio">
              <div class="hero-studio__rail">
                <span class="is-active">写作会话</span>
                <span>素材管理</span>
                <span>书籍学习</span>
                <span>管理后台</span>
              </div>
              <div class="hero-studio__canvas">
                <div class="hero-studio__canvas-head">
                  <div>
                    <small>{{ demoSessionType }}</small>
                    <strong>{{ demoSessionTitle }}</strong>
                  </div>
                  <span>在线</span>
                </div>
                <div class="hero-studio__flow">
                  <span class="is-done">分析请求</span>
                  <span class="is-done">检索素材</span>
                  <span class="is-running">融合规则</span>
                  <span>生成回复</span>
                </div>
                <div class="hero-studio__draft">
                  <h3>关于开展春季安全检查的通知</h3>
                  <p>各单位：为全面排查风险隐患，现就春季安全检查工作通知如下。</p>
                  <p>一是聚焦重点区域开展拉网式检查；二是建立整改台账；三是落实责任到岗到人。</p>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section id="demo" class="section section--showcase">
        <div class="section__head">
          <div>
            <div class="section-kicker">
              产品演示
            </div>
            <h2>从真实界面出发，而不是用一排功能卡片替代产品表达</h2>
          </div>
          <p>
            落地页首先应该让用户理解系统的空间结构和工作关系，所以这里用一组可切换的系统样片，把写作、知识和治理三部分真正讲清楚。
          </p>
        </div>

        <div class="showcase">
          <div class="showcase__preview">
            <div v-if="activeDemo.id === 'conversation'" class="preview-window preview-window--conversation">
              <aside class="preview-window__sidebar">
                <div class="preview-window__label">
                  会话入口
                </div>
                <article class="preview-session preview-session--active">
                  <strong>{{ demoSessionTitle }}</strong>
                  <span>{{ demoSessionType }}</span>
                </article>
                <article class="preview-session">
                  <strong>关于专项整治工作的通报</strong>
                  <span>通报</span>
                </article>
                <article class="preview-session">
                  <strong>季度督导情况报告</strong>
                  <span>报告</span>
                </article>
              </aside>

              <div class="preview-window__main">
                <div class="preview-window__toolbar">
                  <span>分析请求意图</span>
                  <span>搜索素材</span>
                  <span class="is-active">融合书籍风格规则</span>
                  <span>生成回复</span>
                </div>
                <div class="preview-window__messages">
                  <article class="preview-message preview-message--user">
                    请起草关于春季安全检查的通知，强调排查整改和责任落实。
                  </article>
                  <article class="preview-message">
                    已结合通知类模板、历史素材与书籍规则，先输出结构骨架，再补齐执行要求和时间节点。
                  </article>
                </div>
              </div>

              <aside class="preview-window__paper">
                <div class="preview-window__label">
                  正文编辑
                </div>
                <h3>关于开展春季安全检查的通知</h3>
                <p>各单位：为全面排查风险隐患，现就春季安全检查工作通知如下。</p>
                <p>请各单位结合职责抓好排查整改，建立问题台账，明确整改时限和责任分工。</p>
              </aside>
            </div>

            <div v-else-if="activeDemo.id === 'knowledge'" class="preview-window preview-window--knowledge">
              <section class="preview-stack-card">
                <div class="preview-window__label">
                  素材入库
                </div>
                <div class="preview-stack-card__metric">
                  <strong>126</strong>
                  <span>账户素材总量</span>
                </div>
                <div class="preview-bar">
                  <span class="preview-bar__fill preview-bar__fill--wide" />
                </div>
                <ul class="preview-list">
                  <li>自动分类文种、摘要与关键词</li>
                  <li>风格分析结果直接供写作调用</li>
                </ul>
              </section>

              <section class="preview-stack-card">
                <div class="preview-window__label">
                  书籍学习
                </div>
                <div class="preview-stack-card__metric">
                  <strong>4 / 4</strong>
                  <span>扫描完成</span>
                </div>
                <div class="preview-book">
                  <div>
                    <span>机关公文写作要点.pdf</span>
                    <em>OCR 已启用</em>
                  </div>
                  <div>
                    <span>常用文稿范式.epub</span>
                    <em>规则已提炼</em>
                  </div>
                </div>
              </section>

              <section class="preview-stack-card preview-stack-card--wide">
                <div class="preview-window__label">
                  风格规则
                </div>
                <div class="preview-rule-list">
                  <article>通知类先交代目的，再分条列出执行事项。</article>
                  <article>涉及金额、次数、时限时，优先放在执行要求与督导机制段落。</article>
                  <article>避免口号化泛述，优先使用职责主体 + 动作 + 时限的表达结构。</article>
                </div>
              </section>
            </div>

            <div v-else class="preview-window preview-window--governance">
              <section class="preview-stack-card">
                <div class="preview-window__label">
                  账户与用户
                </div>
                <div class="preview-account-list">
                  <div>
                    <strong>华东支队</strong>
                    <span>启用中</span>
                  </div>
                  <div>
                    <strong>机关办公室</strong>
                    <span>6 名用户</span>
                  </div>
                  <div>
                    <strong>后勤保障组</strong>
                    <span>邀请码有效</span>
                  </div>
                </div>
              </section>

              <section class="preview-stack-card preview-stack-card--wide">
                <div class="preview-window__label">
                  角色权限矩阵
                </div>
                <div class="preview-permissions">
                  <div>
                    <span>管理员</span>
                    <em>账户、角色、邀请码、书籍学习</em>
                  </div>
                  <div>
                    <span>写作者</span>
                    <em>会话、素材、导出、正文编辑</em>
                  </div>
                  <div>
                    <span>审核者</span>
                    <em>只读查看与导出留痕</em>
                  </div>
                </div>
              </section>

              <section class="preview-stack-card preview-stack-card--wide">
                <div class="preview-window__label">
                  运维可观测
                </div>
                <ul class="preview-list">
                  <li>书籍导入任务状态、OCR 页数、失败原因可追踪</li>
                  <li>接口错误仅暴露通用信息，日志保留 error_id</li>
                  <li>管理员菜单、路由守卫和按钮显隐按权限统一收口</li>
                </ul>
              </section>
            </div>
          </div>

          <aside class="showcase__aside">
            <div class="showcase-switcher">
              <div class="showcase-switcher__label">
                切换场景
              </div>
              <button
                v-for="scene in demoScenes"
                :key="scene.id"
                type="button"
                class="showcase-tab"
                :class="{ 'is-active': scene.id === activeDemoId }"
                @click="activeDemoId = scene.id"
              >
                <strong class="showcase-tab__title">{{ scene.label }}</strong>
                <small>{{ scene.highlight }}</small>
              </button>
            </div>

            <article class="showcase-note">
              <span>当前场景</span>
              <strong class="showcase-note__label">{{ activeDemo.label }}</strong>
              <h3 class="showcase-note__title">
                {{ activeDemo.title }}
              </h3>
              <p>{{ activeDemo.description }}</p>
              <ul>
                <li v-for="bullet in activeDemo.bullets" :key="bullet">
                  {{ bullet }}
                </li>
              </ul>
            </article>
          </aside>
        </div>
      </section>

      <section id="structure" class="section section--structure">
        <div class="section__head">
          <div>
            <div class="section-kicker">
              能力结构
            </div>
            <h2>围绕正式公文生产，系统当前提供四组核心能力</h2>
          </div>
          <p>
            会话组织、知识增强、正式排版和后台治理共同构成当前系统的前端能力框架，页面表达只聚焦这些实际能力本身。
          </p>
        </div>

        <div class="feature-layout">
          <article v-for="panel in featurePanels" :key="panel.title" class="feature-panel">
            <div class="feature-panel__icon">
              <FaIcon :name="panel.icon" />
            </div>
            <div class="feature-panel__eyebrow">
              {{ panel.eyebrow }}
            </div>
            <h3>{{ panel.title }}</h3>
            <p>{{ panel.description }}</p>
          </article>
        </div>
      </section>

      <section id="workflow" class="section process">
        <div class="process__intro">
          <div class="section-kicker">
            进入路径
          </div>
          <h2>系统按照正式写作节奏组织，而不是按照通用聊天产品节奏组织</h2>
          <p>
            先确定事项，再汇聚知识，再进入 AI 与正文并行工作台，最后由管理员持续治理资源和权限边界。这条路径决定了产品真正能否长期可用。
          </p>
          <div class="process-proof">
            <article>
              <span>路径原则</span>
              <strong>先会话，后工作台</strong>
              <p>登录后不让用户重新寻找入口，而是优先继续最近任务。</p>
            </article>
            <article>
              <span>协作原则</span>
              <strong>先结构，后措辞</strong>
              <p>系统优先提供结构骨架、知识检索和风格规则，再进入正文打磨。</p>
            </article>
          </div>
        </div>

        <div class="process__timeline">
          <article v-for="step in workflowSteps" :key="step.index" class="process-step">
            <span class="process-step__index">{{ step.index }}</span>
            <div class="process-step__body">
              <h3>{{ step.title }}</h3>
              <p>{{ step.description }}</p>
            </div>
            <small>{{ step.result }}</small>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.landing-page {
  --landing-bg: #f3efe8;
  --landing-paper: #fcfaf6;
  --landing-paper-strong: #f8f3ea;
  --landing-ink: #131313;
  --landing-ink-soft: #575146;
  --landing-line: rgb(23 20 17 / 10%);
  --landing-line-strong: rgb(23 20 17 / 16%);
  --landing-shadow: 0 28px 60px rgb(18 18 18 / 8%);
  --landing-shadow-soft: 0 12px 28px rgb(18 18 18 / 6%);

  position: relative;
  min-height: 100vh;
  padding: 26px;
  overflow: hidden;
  color: var(--landing-ink);
  background:
    radial-gradient(circle at top left, rgb(23 20 17 / 5%), transparent 24%),
    linear-gradient(180deg, #f8f4ed 0%, var(--landing-bg) 100%);
}

.landing-page__grain,
.landing-page__halo {
  position: absolute;
  pointer-events: none;
}

.landing-page__grain {
  inset: 0;
  background-image:
    linear-gradient(rgb(23 20 17 / 3%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(23 20 17 / 3%) 1px, transparent 1px);
  background-size: 32px 32px;
  opacity: 0.2;
  mask-image: radial-gradient(circle at center, black 45%, transparent 100%);
}

.landing-page__halo {
  border-radius: 999px;
  opacity: 0.4;
  filter: blur(70px);
}

.landing-page__halo--top {
  top: -120px;
  right: -140px;
  width: 360px;
  height: 360px;
  background: rgb(255 255 255 / 70%);
}

.landing-page__halo--side {
  bottom: 160px;
  left: -120px;
  width: 280px;
  height: 280px;
  background: rgb(72 92 83 / 12%);
}

.landing-topbar,
.landing-main {
  position: relative;
  z-index: 1;
}

.landing-topbar {
  display: flex;
  gap: 20px;
  align-items: center;
  justify-content: space-between;
  width: min(1320px, 100%);
  padding: 14px 18px;
  margin: 0 auto 24px;
  background: rgb(255 252 247 / 74%);
  border: 1px solid var(--landing-line);
  border-radius: 24px;
  box-shadow: var(--landing-shadow-soft);
  backdrop-filter: blur(16px);
}

.landing-brand {
  display: inline-flex;
  gap: 12px;
  align-items: center;
  padding: 0;
  color: var(--landing-ink);
  background: transparent;
  border: none;
}

.landing-brand__mark {
  width: 44px;
  height: 44px;
}

.landing-brand__copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
}

.landing-brand__copy strong {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
}

.landing-brand__copy small {
  font-size: 12px;
  line-height: 1.4;
  color: var(--landing-ink-soft);
}

.landing-topbar__nav {
  display: inline-flex;
  gap: 10px;
  align-items: center;
}

.landing-topbar__nav button,
.landing-topbar__actions :deep(.el-button:not(.el-button--primary)) {
  color: var(--landing-ink-soft);
}

.landing-topbar__nav button {
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  background: transparent;
  border: none;
  border-radius: 999px;
  transition: background 0.2s ease, color 0.2s ease;
}

.landing-topbar__nav button:hover {
  color: var(--landing-ink);
  background: rgb(23 20 17 / 6%);
}

.landing-topbar__actions {
  display: inline-flex;
  gap: 10px;
  align-items: center;
}

.landing-topbar__actions :deep(.el-button),
.hero__actions :deep(.el-button) {
  min-width: 138px;
  height: 42px;
  border-radius: 999px;
}

.landing-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: min(1320px, 100%);
  margin: 0 auto;
}

.hero,
.section {
  background: rgb(255 252 247 / 76%);
  border: 1px solid var(--landing-line);
  border-radius: 32px;
  box-shadow: var(--landing-shadow-soft);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) 430px;
  gap: 22px;
  padding: 32px;
}

.hero__main {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.section-kicker,
.hero-card__eyebrow,
.section__head .section-kicker,
.feature-panel__eyebrow,
.preview-window__label,
.hero-metric__label {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 28px;
  padding: 0 12px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  color: var(--landing-ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgb(23 20 17 / 6%);
  border-radius: 999px;
}

.hero__title,
.section__head h2 {
  margin: 0;
  font-family: "Source Han Serif SC", "Songti SC", STSong, serif;
  line-height: 1.02;
  color: var(--landing-ink);
  letter-spacing: -0.04em;
}

.hero__title {
  max-width: 12ch;
  font-size: clamp(48px, 6vw, 82px);
}

.hero__description,
.section__head p,
.feature-panel p,
.hero-card p,
.showcase-note p,
.preview-list li,
.process-step p,
.process-proof p {
  margin: 0;
  font-size: 15px;
  line-height: 1.9;
  color: var(--landing-ink-soft);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.hero-metric {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 150px;
  padding: 18px;
  background: linear-gradient(180deg, rgb(255 255 255 / 84%) 0%, rgb(246 241 233 / 96%) 100%);
  border: 1px solid var(--landing-line);
  border-radius: 24px;
}

.hero-metric strong {
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
}

.hero-metric p {
  font-size: 13px;
  line-height: 1.8;
}

.hero__rail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: linear-gradient(180deg, rgb(255 255 255 / 84%) 0%, rgb(245 239 231 / 96%) 100%);
  border: 1px solid var(--landing-line);
  border-radius: 26px;
}

.hero-card strong,
.process-step h3,
.feature-panel h3 {
  margin: 0;
  font-size: 22px;
  line-height: 1.35;
  color: var(--landing-ink);
}

.hero-card__meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.hero-card__meta-grid div {
  padding: 12px;
  background: rgb(23 20 17 / 4%);
  border-radius: 16px;
}

.hero-card__meta-grid span {
  display: block;
  margin-bottom: 6px;
}

.hero-card__meta-grid strong {
  font-size: 15px;
}

.hero-studio {
  display: grid;
  grid-template-columns: 122px minmax(0, 1fr);
  gap: 12px;
  min-height: 300px;
}

.hero-studio__rail,
.hero-studio__canvas,
.preview-window__sidebar,
.preview-window__main,
.preview-window__paper,
.preview-stack-card,
.feature-panel,
.process-proof article,
.process-step {
  background: var(--landing-paper);
  border: 1px solid var(--landing-line);
  border-radius: 22px;
}

.hero-studio__rail {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}

.hero-studio__rail span {
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--landing-ink-soft);
  background: rgb(23 20 17 / 4%);
  border-radius: 14px;
}

.hero-studio__rail .is-active {
  color: #fff;
  background: #151515;
}

.hero-studio__canvas {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
}

.hero-studio__canvas-head,
.preview-stack-card__metric,
.preview-account-list div {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.hero-studio__canvas-head small {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--landing-ink-soft);
}

.hero-studio__canvas-head strong {
  font-size: 16px;
}

.hero-studio__canvas-head span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
  color: #2c5c43;
  background: rgb(226 240 232 / 96%);
  border-radius: 999px;
}

.hero-studio__flow,
.preview-window__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-studio__flow span,
.preview-window__toolbar span {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
  color: var(--landing-ink-soft);
  background: rgb(23 20 17 / 5%);
  border-radius: 999px;
}

.hero-studio__flow .is-done,
.preview-window__toolbar .is-done {
  color: #2c5c43;
  background: rgb(226 240 232 / 96%);
}

.hero-studio__flow .is-running,
.preview-window__toolbar .is-active {
  color: #7c4e03;
  background: rgb(247 237 215 / 96%);
}

.hero-studio__draft {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  padding: 18px 16px;
  background: linear-gradient(180deg, #fffdfa 0%, #f8f2e7 100%);
  border: 1px solid var(--landing-line);
  border-radius: 18px;
}

.hero-studio__draft h3,
.preview-window__paper h3 {
  margin: 0;
  font-family: "Source Han Serif SC", "Songti SC", STSong, serif;
  font-size: 20px;
  line-height: 1.35;
  color: var(--landing-ink);
}

.hero-studio__draft p,
.preview-window__paper p {
  margin: 0;
  font-size: 14px;
  line-height: 1.9;
  color: var(--landing-ink-soft);
}

.hero-ledger,
.showcase-note ul,
.preview-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.hero-ledger li,
.showcase-note li,
.preview-list li {
  position: relative;
  padding-left: 16px;
}

.hero-ledger li::before,
.showcase-note li::before,
.preview-list li::before {
  position: absolute;
  top: 10px;
  left: 0;
  width: 6px;
  height: 6px;
  content: "";
  background: #151515;
  border-radius: 999px;
}

.section,
.cta {
  padding: 28px 30px;
}

.section__head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 20px;
  align-items: end;
  margin-bottom: 22px;
}

.section__head h2 {
  max-width: 16ch;
  margin-top: 10px;
  font-size: clamp(30px, 4vw, 48px);
}

.showcase {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.showcase__preview,
.showcase-note,
.showcase-switcher {
  background: linear-gradient(180deg, rgb(255 255 255 / 84%) 0%, rgb(245 239 231 / 96%) 100%);
  border: 1px solid var(--landing-line);
  border-radius: 28px;
}

.showcase__preview {
  padding: 18px;
  box-shadow: var(--landing-shadow);
}

.showcase__aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.showcase-switcher {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
}

.showcase-switcher__label,
.showcase-note span,
.preview-window__label,
.process-proof span {
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  color: var(--landing-ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.showcase-switcher__label {
  padding: 8px 12px 4px;
}

.showcase-tab {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 20px;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.showcase-tab__title {
  margin: 0;
  font-size: 18px;
  line-height: 1.45;
  color: var(--landing-ink);
}

.showcase-tab small {
  font-size: 13px;
  line-height: 1.7;
  color: var(--landing-ink-soft);
}

.showcase-tab:hover,
.showcase-tab.is-active {
  background: rgb(255 255 255 / 62%);
  border-color: var(--landing-line-strong);
  box-shadow: var(--landing-shadow-soft);
  transform: translateY(-1px);
}

.showcase-note {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
}

.showcase-note__label {
  font-size: 18px;
  line-height: 1.45;
  color: var(--landing-ink);
}

.showcase-note__title {
  margin: 0;
  font-size: 24px;
  line-height: 1.35;
  color: var(--landing-ink);
}

.preview-window {
  min-height: 500px;
}

.preview-window--conversation {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 280px;
  gap: 14px;
}

.preview-window--knowledge,
.preview-window--governance {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.preview-window__sidebar,
.preview-window__main,
.preview-window__paper,
.preview-stack-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.preview-session,
.preview-message,
.preview-book div,
.preview-rule-list article,
.preview-permissions div,
.preview-account-list div {
  padding: 12px 14px;
  background: rgb(23 20 17 / 4%);
  border-radius: 16px;
}

.preview-session {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-session strong,
.preview-book span,
.preview-permissions span,
.preview-account-list strong {
  font-size: 14px;
  line-height: 1.5;
  color: var(--landing-ink);
}

.preview-session span,
.preview-book em,
.preview-permissions em,
.preview-account-list span {
  font-size: 12px;
  font-style: normal;
  line-height: 1.6;
  color: var(--landing-ink-soft);
}

.preview-session--active {
  color: #fff;
  background: #151515;
}

.preview-session--active strong,
.preview-session--active span {
  color: #fff;
}

.preview-window__main {
  min-width: 0;
}

.preview-window__messages,
.preview-rule-list,
.preview-permissions,
.preview-book,
.preview-account-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preview-message {
  max-width: 88%;
  font-size: 14px;
  line-height: 1.85;
  color: var(--landing-ink);
  background: #fff;
  border-radius: 18px 18px 18px 8px;
}

.preview-message--user {
  margin-left: auto;
  color: #fff;
  background: #151515;
  border-radius: 18px 18px 8px;
}

.preview-window__paper {
  background: linear-gradient(180deg, #fffdfa 0%, #f7f1e7 100%);
}

.preview-stack-card--wide {
  grid-column: span 2;
}

.preview-stack-card__metric strong {
  font-size: 28px;
  line-height: 1;
}

.preview-stack-card__metric span {
  font-size: 13px;
  color: var(--landing-ink-soft);
}

.preview-bar {
  height: 10px;
  overflow: hidden;
  background: rgb(23 20 17 / 8%);
  border-radius: 999px;
}

.preview-bar__fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #151515 0%, #6d675d 100%);
  border-radius: inherit;
}

.preview-bar__fill--wide {
  width: 72%;
}

.feature-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.feature-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 220px;
  padding: 22px;
}

.feature-panel__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  font-size: 22px;
  color: var(--landing-ink);
  background: rgb(23 20 17 / 6%);
  border-radius: 14px;
}

.process {
  display: grid;
  grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}

.process__intro {
  display: flex;
  flex-direction: column;
  gap: 18px;
  justify-content: space-between;
  min-height: 100%;
}

.process__intro h2 {
  margin: 0;
  font-family: "Source Han Serif SC", "Songti SC", STSong, serif;
  font-size: clamp(30px, 4vw, 46px);
  line-height: 1.06;
  letter-spacing: -0.04em;
}

.process-proof {
  display: grid;
  gap: 12px;
  margin-top: auto;
}

.process-proof article,
.process-step {
  padding: 18px;
}

.process-proof strong,
.process-step small {
  display: block;
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--landing-ink);
}

.process__timeline {
  display: grid;
  gap: 12px;
  align-content: start;
}

.process-step {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.process-step__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  font-size: 22px;
  font-weight: 700;
  color: var(--landing-ink);
  background: rgb(23 20 17 / 6%);
  border-radius: 20px;
}

.process-step__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@supports not ((backdrop-filter: blur(1px))) {
  .landing-topbar {
    background: rgb(255 252 247 / 94%);
  }
}

@media (max-width: 1240px) {
  .hero,
  .showcase,
  .process,
  .section__head,
  .feature-layout {
    grid-template-columns: 1fr;
  }

  .hero__title {
    max-width: none;
  }

  .preview-window--conversation,
  .preview-window--knowledge,
  .preview-window--governance {
    grid-template-columns: 1fr;
  }

  .preview-stack-card--wide {
    grid-column: auto;
  }
}

@media (max-width: 900px) {
  .landing-page {
    padding: 16px;
  }

  .landing-topbar,
  .landing-topbar__actions,
  .landing-main,
  .hero,
  .hero__metrics,
  .hero__rail,
  .showcase,
  .showcase__aside,
  .feature-layout,
  .process,
  .process__timeline {
    gap: 14px;
  }

  .landing-topbar,
  .hero,
  .section {
    padding: 18px;
  }

  .landing-topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .landing-topbar__nav {
    display: none;
  }

  .landing-topbar__actions,
  .hero__actions {
    flex-direction: column;
    align-items: stretch;
  }

  .landing-topbar__actions :deep(.el-button),
  .hero__actions :deep(.el-button) {
    width: 100%;
  }

  .hero__metrics {
    grid-template-columns: 1fr;
  }

  .hero-studio {
    grid-template-columns: 1fr;
  }

  .section__head h2,
  .process__intro h2 {
    max-width: none;
  }

  .process-step {
    grid-template-columns: 1fr;
  }

  .process-step__index {
    width: 54px;
    height: 54px;
    border-radius: 18px;
  }
}
</style>

export interface SeoMetaInput {
  title?: string
  description?: string
  keywords?: string[]
  path?: string
  image?: string
  robots?: string
  type?: string
  locale?: string
  siteName?: string
}

const APP_TITLE = import.meta.env.VITE_APP_TITLE || '公文写作系统'
const DEFAULT_DESCRIPTION = '面向正式公文场景的团队级智能写作平台，统一会话写作、素材治理、书籍学习、风格增强与权限管理。'
const DEFAULT_KEYWORDS = ['公文写作系统', '公文写作', '智能写作', 'AI公文', '素材管理', '书籍学习', 'RBAC']

const DEFAULT_SEO_META: Required<SeoMetaInput> = {
  title: APP_TITLE,
  description: DEFAULT_DESCRIPTION,
  keywords: DEFAULT_KEYWORDS,
  path: '/',
  image: '/og-cover.png',
  robots: 'index,follow',
  type: 'website',
  locale: 'zh_CN',
  siteName: APP_TITLE,
}

function getSiteOrigin() {
  const configured = import.meta.env.VITE_SITE_URL?.trim()
  if (configured && /^https?:\/\//i.test(configured)) {
    return configured.replace(/\/+$/, '')
  }
  if (typeof window !== 'undefined' && window.location.origin) {
    return window.location.origin
  }
  return ''
}

function resolveUrl(target: string) {
  if (/^https?:\/\//i.test(target)) {
    return target
  }
  const normalized = target.startsWith('/') ? target : `/${target}`
  const origin = getSiteOrigin()
  return origin ? `${origin}${normalized}` : normalized
}

function serializeKeywords(keywords: string[]) {
  return [...new Set(keywords.map(item => item.trim()).filter(Boolean))].join('，')
}

function upsertMetaTag(selector: string, attrs: Record<string, string>) {
  if (typeof document === 'undefined') {
    return
  }
  let element = document.head.querySelector<HTMLMetaElement>(selector)
  if (!element) {
    element = document.createElement('meta')
    document.head.appendChild(element)
  }
  Object.entries(attrs).forEach(([key, value]) => {
    element.setAttribute(key, value)
  })
}

function upsertLinkTag(selector: string, attrs: Record<string, string>) {
  if (typeof document === 'undefined') {
    return
  }
  let element = document.head.querySelector<HTMLLinkElement>(selector)
  if (!element) {
    element = document.createElement('link')
    document.head.appendChild(element)
  }
  Object.entries(attrs).forEach(([key, value]) => {
    element.setAttribute(key, value)
  })
}

export function applySeoMeta(input: SeoMetaInput = {}) {
  if (typeof document === 'undefined') {
    return
  }

  const meta = {
    ...DEFAULT_SEO_META,
    ...input,
    keywords: input.keywords?.length ? input.keywords : DEFAULT_SEO_META.keywords,
  }

  const title = meta.title.trim() || APP_TITLE
  const canonical = resolveUrl(meta.path)
  const image = resolveUrl(meta.image)
  const keywords = serializeKeywords(meta.keywords)

  document.title = title

  upsertLinkTag('link[data-seo-link="canonical"], link[rel="canonical"]', {
    'rel': 'canonical',
    'href': canonical,
    'data-seo-link': 'canonical',
  })

  upsertMetaTag('meta[data-seo-name="description"], meta[name="description"]', {
    'name': 'description',
    'content': meta.description,
    'data-seo-name': 'description',
  })
  upsertMetaTag('meta[data-seo-name="keywords"], meta[name="keywords"]', {
    'name': 'keywords',
    'content': keywords,
    'data-seo-name': 'keywords',
  })
  upsertMetaTag('meta[data-seo-name="robots"], meta[name="robots"]', {
    'name': 'robots',
    'content': meta.robots,
    'data-seo-name': 'robots',
  })
  upsertMetaTag('meta[data-seo-name="theme-color"], meta[name="theme-color"]', {
    'name': 'theme-color',
    'content': '#f3efe8',
    'data-seo-name': 'theme-color',
  })
  upsertMetaTag('meta[data-seo-name="application-name"], meta[name="application-name"]', {
    'name': 'application-name',
    'content': meta.siteName,
    'data-seo-name': 'application-name',
  })
  upsertMetaTag('meta[data-seo-name="apple-mobile-web-app-title"], meta[name="apple-mobile-web-app-title"]', {
    'name': 'apple-mobile-web-app-title',
    'content': meta.siteName,
    'data-seo-name': 'apple-mobile-web-app-title',
  })
  upsertMetaTag('meta[data-seo-name="twitter:card"], meta[name="twitter:card"]', {
    'name': 'twitter:card',
    'content': 'summary_large_image',
    'data-seo-name': 'twitter:card',
  })
  upsertMetaTag('meta[data-seo-name="twitter:title"], meta[name="twitter:title"]', {
    'name': 'twitter:title',
    'content': title,
    'data-seo-name': 'twitter:title',
  })
  upsertMetaTag('meta[data-seo-name="twitter:description"], meta[name="twitter:description"]', {
    'name': 'twitter:description',
    'content': meta.description,
    'data-seo-name': 'twitter:description',
  })
  upsertMetaTag('meta[data-seo-name="twitter:image"], meta[name="twitter:image"]', {
    'name': 'twitter:image',
    'content': image,
    'data-seo-name': 'twitter:image',
  })

  upsertMetaTag('meta[data-seo-property="og:type"], meta[property="og:type"]', {
    'property': 'og:type',
    'content': meta.type,
    'data-seo-property': 'og:type',
  })
  upsertMetaTag('meta[data-seo-property="og:site_name"], meta[property="og:site_name"]', {
    'property': 'og:site_name',
    'content': meta.siteName,
    'data-seo-property': 'og:site_name',
  })
  upsertMetaTag('meta[data-seo-property="og:title"], meta[property="og:title"]', {
    'property': 'og:title',
    'content': title,
    'data-seo-property': 'og:title',
  })
  upsertMetaTag('meta[data-seo-property="og:description"], meta[property="og:description"]', {
    'property': 'og:description',
    'content': meta.description,
    'data-seo-property': 'og:description',
  })
  upsertMetaTag('meta[data-seo-property="og:url"], meta[property="og:url"]', {
    'property': 'og:url',
    'content': canonical,
    'data-seo-property': 'og:url',
  })
  upsertMetaTag('meta[data-seo-property="og:image"], meta[property="og:image"]', {
    'property': 'og:image',
    'content': image,
    'data-seo-property': 'og:image',
  })
  upsertMetaTag('meta[data-seo-property="og:image:alt"], meta[property="og:image:alt"]', {
    'property': 'og:image:alt',
    'content': `${meta.siteName}产品封面图`,
    'data-seo-property': 'og:image:alt',
  })
  upsertMetaTag('meta[data-seo-property="og:locale"], meta[property="og:locale"]', {
    'property': 'og:locale',
    'content': meta.locale,
    'data-seo-property': 'og:locale',
  })
}

export function resetSeoMeta() {
  applySeoMeta(DEFAULT_SEO_META)
}

export { DEFAULT_SEO_META }

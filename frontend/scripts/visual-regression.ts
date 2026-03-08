import type { Page } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

interface LayoutPressure {
  selector: string
  overflowPx: number
  clientWidth: number
  scrollWidth: number
}

interface LayoutReport {
  documentOverflowPx: number
  pressuredContainers: LayoutPressure[]
}

type RouteExpectation = RegExp | string | ((route: string) => boolean)

interface CaptureSpec {
  name: string
  path: string
  expectedRoute?: RouteExpectation
  ignoreSelectors?: string[]
  waitFor: (page: Page) => Promise<void>
  prepare?: (page: Page) => Promise<void>
}

interface CaptureResult {
  name: string
  viewport: string
  route: string
  finalUrl: string
  report: LayoutReport
}

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))
const defaultDate = new Date().toISOString().slice(0, 10)
const baseUrl = process.env.WRITER_E2E_BASE_URL || 'http://127.0.0.1:9000'
const username = requiredEnv('WRITER_E2E_USERNAME')
const password = requiredEnv('WRITER_E2E_PASSWORD')
const captureDate = process.env.WRITER_VISUAL_DATE || defaultDate
const outputRoot = process.env.WRITER_VISUAL_OUTPUT_ROOT
  ? path.resolve(process.cwd(), process.env.WRITER_VISUAL_OUTPUT_ROOT)
  : path.resolve(repoRoot, 'docs', 'ui-baseline')
const roundRoot = path.join(outputRoot, captureDate)
const viewportDir = path.join(roundRoot, 'viewport')
const reportPath = path.join(roundRoot, 'layout-check.generated.md')

const desktopViewport = { width: 1440, height: 1100 }
const mobileViewport = { width: 390, height: 844 }

const TEXT = {
  login: '\u767B\u5F55',
  usernamePlaceholder: '\u8BF7\u8F93\u5165\u7528\u6237\u540D',
  passwordPlaceholder: '\u8BF7\u8F93\u5165\u5BC6\u7801',
  writerSessions: '\u5199\u4F5C\u4F1A\u8BDD',
  newSession: '\u65B0\u5EFA\u4F1A\u8BDD',
  createSession: '\u521B\u5EFA\u4F1A\u8BDD',
  editorTab: '\u6587\u7A3F\u533A',
  bookLearning: '\u4E66\u7C4D\u5B66\u4E60',
  adminAccounts: '\u8D26\u6237\u4E0E\u7528\u6237',
  adminRoles: '\u89D2\u8272\u4E0E\u6743\u9650',
  editorPanelTitle: '\u6B63\u6587\u8349\u7A3F',
} as const

const desktopCaptures: CaptureSpec[] = [
  {
    name: 'writer-sessions-desktop',
    path: '/chat',
    ignoreSelectors: ['.tox'],
    waitFor: waitForSessionHome,
  },
  {
    name: 'writer-workspace-desktop',
    path: '/chat',
    expectedRoute: /^\/chat\/\d+$/,
    ignoreSelectors: ['.tox'],
    prepare: ensureWriterWorkspace,
    waitFor: waitForWorkspaceChat,
  },
  {
    name: 'book-learning-desktop',
    path: '/book-learning',
    waitFor: page => waitForPageTitle(page, TEXT.bookLearning),
  },
  {
    name: 'admin-accounts-desktop',
    path: '/admin/accounts',
    waitFor: page => waitForPageTitle(page, TEXT.adminAccounts),
  },
  {
    name: 'admin-roles-desktop',
    path: '/admin/roles',
    waitFor: page => waitForPageTitle(page, TEXT.adminRoles),
  },
]

const mobileCaptures: CaptureSpec[] = [
  {
    name: 'writer-sessions-mobile',
    path: '/chat',
    waitFor: waitForSessionHome,
  },
  {
    name: 'writer-workspace-mobile-chat',
    path: '/chat',
    expectedRoute: /^\/chat\/\d+$/,
    ignoreSelectors: ['.tox'],
    prepare: ensureWriterWorkspace,
    waitFor: waitForWorkspaceChat,
  },
  {
    name: 'writer-workspace-mobile-editor',
    path: '/chat',
    expectedRoute: /^\/chat\/\d+$/,
    ignoreSelectors: ['.tox'],
    prepare: async (page) => {
      await ensureWriterWorkspace(page)
      await page.getByText(TEXT.editorTab, { exact: true }).click()
      await page.waitForTimeout(300)
    },
    waitFor: waitForWorkspaceEditor,
  },
]

function requiredEnv(name: string) {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

function buildUrl(routePath: string) {
  const normalizedBase = baseUrl.replace(/\/+$/, '')
  return `${normalizedBase}/#${routePath}`
}

function currentAppRoute(page: Page) {
  const currentUrl = new URL(page.url())
  return currentUrl.hash.startsWith('#')
    ? currentUrl.hash.slice(1) || '/'
    : currentUrl.pathname
}

async function ensureLoggedIn(page: Page) {
  await page.goto(buildUrl('/login'), { waitUntil: 'domcontentloaded' })
  await waitForAppSettled(page)

  const loginButton = page.getByRole('button', { name: TEXT.login })
  if (await loginButton.count() === 0) {
    return
  }

  await page.getByPlaceholder(TEXT.usernamePlaceholder).fill(username)
  await page.getByPlaceholder(TEXT.passwordPlaceholder).fill(password)
  await Promise.all([
    page.waitForURL(url => !url.hash.endsWith('/login'), { timeout: 20000 }).catch(() => null),
    loginButton.click(),
  ])
  await waitForAppSettled(page)
}

async function waitForAppSettled(page: Page) {
  await page.waitForLoadState('domcontentloaded')
  await page.waitForLoadState('networkidle').catch(() => null)
  await page.waitForTimeout(400)
  await page.waitForFunction(() => {
    const masks = Array.from(document.querySelectorAll<HTMLElement>('.el-loading-mask'))
    return masks.every((mask) => {
      const style = window.getComputedStyle(mask)
      const rect = mask.getBoundingClientRect()
      return style.display === 'none'
        || style.visibility === 'hidden'
        || Number(style.opacity || '1') === 0
        || rect.width === 0
        || rect.height === 0
    })
  }, undefined, { timeout: 8000 }).catch(() => null)
}

async function waitForPageTitle(page: Page, title: string) {
  await page.locator('h2.page-title').filter({ hasText: title }).first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
}

async function waitForSessionHome(page: Page) {
  await waitForPageTitle(page, TEXT.writerSessions)
  await page.locator('.writing-session-sidebar').first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
}

async function waitForWorkspaceChat(page: Page) {
  await page.locator('.writing-workspace').first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
  await page.locator('.writing-composer').first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
}

async function waitForWorkspaceEditor(page: Page) {
  await page.locator('.writing-workspace').first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
  await page.locator('.writing-editor-pane').first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
  await page.getByText(TEXT.editorPanelTitle, { exact: true }).first().waitFor({
    state: 'visible',
    timeout: 20000,
  })
}

async function ensureWriterWorkspace(page: Page) {
  await waitForSessionHome(page)
  const sessionItems = page.locator('.writing-session-sidebar__item')
  if (await sessionItems.count()) {
    await sessionItems.first().click()
  }
  else {
    await page.getByRole('button', { name: TEXT.newSession }).click()
    const dialog = page.locator('.el-dialog').last()
    await dialog.waitFor({ state: 'visible', timeout: 10000 })
    await dialog.getByRole('textbox').first().fill(`\u89C6\u89C9\u56DE\u5F52\u4F1A\u8BDD ${Date.now()}`)
    await Promise.all([
      page.waitForURL(url => /#\/chat\/\d+$/.test(url.toString()), { timeout: 20000 }).catch(() => null),
      dialog.getByRole('button', { name: TEXT.createSession }).click(),
    ])
  }
  await waitForAppSettled(page)
  await waitForWorkspaceChat(page)
}

function matchesRoute(route: string, expected?: RouteExpectation) {
  if (!expected) {
    return true
  }
  if (typeof expected === 'string') {
    return route === expected
  }
  if (expected instanceof RegExp) {
    return expected.test(route)
  }
  return expected(route)
}

async function openAndCapture(page: Page, spec: CaptureSpec, viewportLabel: string, results: CaptureResult[]) {
  await page.goto(buildUrl(spec.path), { waitUntil: 'domcontentloaded' })
  await waitForAppSettled(page)
  if (spec.prepare) {
    await spec.prepare(page)
    await waitForAppSettled(page)
  }
  await spec.waitFor(page)
  await waitForAppSettled(page)

  const finalRoute = currentAppRoute(page)
  const expectedRoute = spec.expectedRoute || spec.path
  if (!matchesRoute(finalRoute, expectedRoute)) {
    throw new Error(`Unexpected route for ${spec.name}: expected ${String(expectedRoute)}, received ${finalRoute}`)
  }

  const report = await collectLayoutReport(page, spec.ignoreSelectors || [])
  results.push({
    name: spec.name,
    viewport: viewportLabel,
    route: spec.path,
    finalUrl: page.url(),
    report,
  })

  await page.screenshot({
    path: path.join(viewportDir, `${spec.name}.png`),
    fullPage: false,
  })
}

async function collectLayoutReport(page: Page, ignoreSelectors: string[]) {
  return page.evaluate(({ ignoreSelectors }) => {
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const ignoredRoots = [] as HTMLElement[]
    for (const selector of ignoreSelectors) {
      ignoredRoots.push(...Array.from(document.querySelectorAll<HTMLElement>(selector)))
    }

    const documentOverflowPx = Math.max(0, Math.round(Math.max(
      document.documentElement.scrollWidth,
      document.body?.scrollWidth || 0,
    ) - document.documentElement.clientWidth))

    const pressuredContainers = [] as LayoutPressure[]

    for (const element of Array.from(document.querySelectorAll<HTMLElement>('body *'))) {
      let ignored = false
      for (const root of ignoredRoots) {
        if (root === element || root.contains(element)) {
          ignored = true
          break
        }
      }
      if (ignored) {
        continue
      }

      const rect = element.getBoundingClientRect()
      const overflowPx = Math.round(element.scrollWidth - element.clientWidth)
      if (overflowPx < 32) {
        continue
      }
      if (rect.width < 180 || rect.height < 24) {
        continue
      }
      if (rect.bottom < 0 || rect.top > viewportHeight || rect.right < 0 || rect.left > viewportWidth) {
        continue
      }

      let selector = element.tagName.toLowerCase()
      if (element.id) {
        selector = `#${element.id}`
      }
      else if (typeof element.className === 'string') {
        const className = element.className.trim().split(/\s+/).filter(Boolean).slice(0, 3).join('.')
        if (className) {
          selector = `${selector}.${className}`
        }
      }

      pressuredContainers.push({
        selector,
        overflowPx,
        clientWidth: Math.round(element.clientWidth),
        scrollWidth: Math.round(element.scrollWidth),
      })
    }

    pressuredContainers.sort((left, right) => right.overflowPx - left.overflowPx)
    return {
      documentOverflowPx,
      pressuredContainers: pressuredContainers.slice(0, 8),
    }
  }, { ignoreSelectors })
}

function formatReport(entries: CaptureResult[]) {
  const lines = [
    `# Layout Check ${captureDate}`,
    '',
    'Viewport-first automated capture report.',
    '',
  ]

  for (const entry of entries) {
    lines.push(`## ${entry.name}`)
    lines.push(`- Route: \`${entry.route}\``)
    lines.push(`- Viewport: ${entry.viewport}`)
    lines.push(`- Final URL: \`${entry.finalUrl}\``)
    lines.push(`- Document overflow: ${entry.report.documentOverflowPx}px`)
    if (entry.report.pressuredContainers.length) {
      lines.push('- Width pressure containers:')
      for (const container of entry.report.pressuredContainers) {
        lines.push(`  - \`${container.selector}\`: +${container.overflowPx}px (${container.clientWidth}px -> ${container.scrollWidth}px)`)
      }
    }
    else {
      lines.push('- Width pressure containers: none')
    }
    lines.push('')
  }

  return lines.join('\n')
}

async function main() {
  mkdirSync(viewportDir, { recursive: true })

  const browser = await chromium.launch({
    headless: process.env.WRITER_E2E_HEADLESS !== 'false',
  })

  const results: CaptureResult[] = []

  try {
    const desktopContext = await browser.newContext({
      viewport: desktopViewport,
      deviceScaleFactor: 1,
    })
    const desktopPage = await desktopContext.newPage()
    await ensureLoggedIn(desktopPage)
    for (const spec of desktopCaptures) {
      await openAndCapture(desktopPage, spec, `${desktopViewport.width}x${desktopViewport.height}`, results)
    }

    const authState = await desktopContext.storageState()
    const mobileContext = await browser.newContext({
      viewport: mobileViewport,
      isMobile: true,
      hasTouch: true,
      storageState: authState,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    })
    const mobilePage = await mobileContext.newPage()
    for (const spec of mobileCaptures) {
      await openAndCapture(mobilePage, spec, `${mobileViewport.width}x${mobileViewport.height}`, results)
    }

    writeFileSync(reportPath, formatReport(results), 'utf8')

    const blocking = results.filter(entry => entry.report.documentOverflowPx > 0)
    if (blocking.length) {
      const names = blocking.map(item => item.name).join(', ')
      throw new Error(`Document-level horizontal overflow detected: ${names}`)
    }

    console.log(`visual regression completed: ${results.length} captures`)
    console.log(`screenshots: ${viewportDir}`)
    console.log(`report: ${reportPath}`)
  }
  finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})

import type { PluginOption } from 'vite'
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const APP_LOADING_PLACEHOLDER = /%VITE_APP_TITLE%/g
const APP_LOADING_WRAPPER_STYLE = 'position: fixed; top: 0; left: 0; z-index: 10000; width: 100vw; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; user-select: none;'

interface AppLoadingOptions {
  appTitle: string
  htmlPath: string
}

function loadAppLoadingHtml({ appTitle, htmlPath }: AppLoadingOptions) {
  const resolvedPath = path.resolve(process.cwd(), htmlPath)
  const template = fs.readFileSync(resolvedPath, 'utf8')
  return template.replace(APP_LOADING_PLACEHOLDER, appTitle)
}

export function createAppLoadingPlugin(options: AppLoadingOptions): PluginOption {
  const loadingHtml = loadAppLoadingHtml(options)
  const wrappedLoadingHtml = `<div data-app-loading style="${APP_LOADING_WRAPPER_STYLE}">${loadingHtml}</div>`

  return {
    name: 'writer-app-loading',
    enforce: 'pre',
    transformIndexHtml(html) {
      return html.replace(/<\/body>/i, `${wrappedLoadingHtml}</body>`)
    },
  }
}

import type { PluginOption } from 'vite'
import path from 'node:path'
import process from 'node:process'
import vueLegacy from '@vitejs/plugin-legacy'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import Unocss from 'unocss/vite'
import autoImport from 'unplugin-auto-import/vite'
import TurboConsole from 'unplugin-turbo-console/vite'
import components from 'unplugin-vue-components/vite'
import { loadEnv } from 'vite'
import AppLoading from 'vite-plugin-app-loading'
import Archiver from 'vite-plugin-archiver'
import { compression } from 'vite-plugin-compression2'
import { envParse, parseLoadedEnv } from 'vite-plugin-env-parse'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'
import VueDevTools from 'vite-plugin-vue-devtools'

export default function createVitePlugins(mode: string, isBuild = false) {
  const viteEnv = parseLoadedEnv(loadEnv(mode, process.cwd()))
  const vitePlugins: (PluginOption | PluginOption[])[] = [
    vue(),
    vueJsx(),
    vueLegacy({
      renderLegacyChunks: false,
      modernPolyfills: [
        'es.array.at',
        'es.array.find-last',
        'es.object.has-own',
      ],
    }),
    viteEnv.VITE_OPEN_DEVTOOLS && VueDevTools({
      launchEditor: viteEnv.VITE_VUE_DEVTOOLS_LAUNCH_EDITOR ?? 'vscode',
    }),
    envParse({
      dtsPath: 'src/types/env.d.ts',
    }),
    autoImport({
      imports: [
        'vue',
        'vue-router',
        'pinia',
      ],
      dts: './src/types/auto-imports.d.ts',
      dirs: [
        './src/store/modules',
        './src/utils/composables',
      ],
    }),
    components({
      globs: [
        'src/ui/components/*/index.vue',
        'src/components/*/index.vue',
      ],
      dts: './src/types/components.d.ts',
    }),
    Unocss(),
    createSvgIconsPlugin({
      iconDirs: [path.resolve(process.cwd(), 'src/assets/icons/')],
      symbolId: 'icon-[dir]-[name]',
      svgoOptions: isBuild,
    }),
    viteEnv.VITE_BUILD_COMPRESS && compression({
      exclude: [/\.(br)$/, /\.(gz)$/],
      algorithms: viteEnv.VITE_BUILD_COMPRESS.split(',').map((item: string) => ({
        gzip: 'gzip',
        brotli: 'brotliCompress',
      }[item])),
    }),
    viteEnv.VITE_BUILD_ARCHIVE && Archiver({
      archiveType: viteEnv.VITE_BUILD_ARCHIVE,
    }),
    AppLoading('loading.html'),
    TurboConsole(),
  ]
  return vitePlugins
}

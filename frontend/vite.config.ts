import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import dayjs from 'dayjs'
import { defineConfig, loadEnv } from 'vite'
import pkg from './package.json'
import createVitePlugins from './vite/plugins'

const manualChunkGroups = [
  {
    name: 'tinymce-vendor',
    matchers: ['/tinymce/', '/@tinymce/tinymce-vue/'],
  },
  {
    name: 'element-plus-vendor',
    matchers: ['/element-plus/', '/@element-plus/icons-vue/'],
  },
  {
    name: 'framework-vendor',
    matchers: ['/vue/', '/vue-router/', '/pinia/', '/@vueuse/'],
  },
  {
    name: 'writer-vendor',
    matchers: ['/markdown-it/', '/dompurify/', '/dayjs/', '/axios/', '/es-toolkit/'],
  },
  {
    name: 'ui-vendor',
    matchers: ['/reka-ui/', '/lucide-vue-next/', '/class-variance-authority/', '/clsx/', '/tailwind-merge/'],
  },
] as const

function resolveManualChunk(id: string) {
  const normalizedId = id.replace(/\\/g, '/')
  if (!normalizedId.includes('/node_modules/')) {
    return undefined
  }

  for (const group of manualChunkGroups) {
    if (group.matchers.some(matcher => normalizedId.includes(matcher))) {
      return group.name
    }
  }

  return undefined
}

// https://vitejs.dev/config/
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd())
  // ?? scss ??
  const scssResources: string[] = []
  fs.readdirSync('src/assets/styles/resources').forEach((dirname) => {
    if (fs.statSync(`src/assets/styles/resources/${dirname}`).isFile()) {
      scssResources.push(`@use "/src/assets/styles/resources/${dirname}" as *;`)
    }
  })
  return {
    // ??????? https://cn.vitejs.dev/config/server-options
    server: {
      open: true,
      host: true,
      port: 9000,
      proxy: {
        '/proxy': {
          target: env.VITE_APP_API_BASEURL,
          changeOrigin: command === 'serve' && env.VITE_OPEN_PROXY === 'true',
          rewrite: path => path.replace(/\/proxy/, ''),
        },
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    // ???? https://cn.vitejs.dev/config/build-options
    build: {
      outDir: mode === 'production' ? 'dist' : `dist-${mode}`,
      sourcemap: env.VITE_BUILD_SOURCEMAP === 'true',
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          manualChunks: resolveManualChunk,
        },
      },
    },
    define: {
      __SYSTEM_INFO__: JSON.stringify({
        pkg: {
          version: pkg.version,
          dependencies: pkg.dependencies,
          devDependencies: pkg.devDependencies,
        },
        lastBuildTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      }),
    },
    plugins: createVitePlugins(mode, command === 'build'),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '#': path.resolve(__dirname, 'src/types'),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: scssResources.join(''),
        },
      },
    },
  }
})

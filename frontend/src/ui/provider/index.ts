import type { App } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

function install(app: App) {
  app.use(ElementPlus)
}

export default { install }

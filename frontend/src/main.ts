// ???????????????
// ??????
import directive from '@/utils/directive'

import App from './App.vue'
import router from './router'
import pinia from './store'
import uiProvider from './ui/provider'
import '@/utils/systemCopyright'

// ?? SVG ???
import 'virtual:svg-icons-register'
// UnoCSS
import '@unocss/reset/tailwind-compat.css'
import 'virtual:uno.css'
// ????? token ???????
import '@/assets/styles/globals.css'
import '@/assets/styles/page-system.css'

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(uiProvider)
directive(app)

app.mount('#app')

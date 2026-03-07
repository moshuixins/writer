const APP_LOADING_SELECTOR = '[data-app-loading]'
const APP_LOADING_TRANSITION = 'all 0.5s ease-out'

export function loadingFadeOut() {
  const loadingEl = document.querySelector<HTMLElement>(APP_LOADING_SELECTOR)
  if (!loadingEl) {
    return
  }

  loadingEl.style.pointerEvents = 'none'
  loadingEl.style.visibility = 'hidden'
  loadingEl.style.opacity = '0'
  loadingEl.style.transition = APP_LOADING_TRANSITION
  loadingEl.addEventListener('transitionend', () => loadingEl.remove(), { once: true })
}

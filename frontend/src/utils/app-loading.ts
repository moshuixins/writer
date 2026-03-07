const APP_LOADING_SELECTOR = '[data-app-loading]'
const APP_LOADING_TRANSITION = 'opacity 0.35s ease-out'
const APP_LOADING_REMOVE_DELAY_MS = 450

export function loadingFadeOut() {
  const loadingEl = document.querySelector<HTMLElement>(APP_LOADING_SELECTOR)
  if (!loadingEl || loadingEl.dataset.state === 'closing') {
    return
  }

  loadingEl.dataset.state = 'closing'
  loadingEl.style.pointerEvents = 'none'
  loadingEl.style.transition = APP_LOADING_TRANSITION
  loadingEl.style.opacity = '0'

  const cleanup = () => {
    if (!loadingEl.isConnected) {
      return
    }
    loadingEl.style.visibility = 'hidden'
    loadingEl.remove()
  }

  loadingEl.addEventListener('transitionend', cleanup, { once: true })
  window.setTimeout(cleanup, APP_LOADING_REMOVE_DELAY_MS)
}

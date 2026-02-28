import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '../api'

interface UserInfo {
  id: number
  username: string
  display_name: string
  department: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(t: string, u: UserInfo) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  function restoreUser() {
    const saved = localStorage.getItem('user')
    if (saved && token.value) {
      try {
        user.value = JSON.parse(saved)
      } catch {
        logout()
      }
    }
  }

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    setAuth(data.token, data.user)
  }

  async function register(username: string, password: string, display_name: string) {
    const { data } = await api.post('/auth/register', {
      username, password, display_name,
    })
    setAuth(data.token, data.user)
  }

  return { token, user, isLoggedIn, login, register, logout, restoreUser }
})

import { defineStore } from 'pinia'
import type { LoginData, MeData } from '@/types'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('lg_token') || '',
    user: null as null | Pick<LoginData, 'user_id' | 'username'>,
    me: null as null | MeData,
  }),
  getters: {
    loggedIn: s => !!s.token,
  },
  actions: {
    setLogin(data: LoginData) {
      this.token = data.token
      this.user = { user_id: data.user_id, username: data.username }
      localStorage.setItem('lg_token', data.token)
    },
    setMe(data: MeData) {
      this.me = data
    },
    logout() {
      this.token = ''
      this.user = null
      this.me = null
      localStorage.removeItem('lg_token')

      Object.keys(localStorage)
          .filter(k => k.startsWith('lg_chat_session_'))
          .forEach(k => localStorage.removeItem(k))
    },
  },
})
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/Register.vue') },

    { path: '/home', name: 'home', component: () => import('@/views/Home.vue'), meta: { auth: true } },

    {
      path: '/repair',
      name: 'repair',
      component: () => import('@/views/Chat.vue'),
      meta: { auth: true, scene: 'REPAIR', title: '报修 / 工单' },
    },
    {
      path: '/lease',
      name: 'lease',
      component: () => import('@/views/Chat.vue'),
      meta: { auth: true, scene: 'CHECKOUT', title: '租约 / 退租 / 结算' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminRag.vue'),
      meta: { auth: true, title: '知识库管理' },
    },

    { path: '/chat', redirect: '/home' },
  ],
})

router.beforeEach(to => {
  const auth = useAuthStore()

  if (to.meta.auth && !auth.loggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if ((to.name === 'login' || to.name === 'register') && auth.loggedIn) {
    return { path: '/home' }
  }

  return true
})

export default router
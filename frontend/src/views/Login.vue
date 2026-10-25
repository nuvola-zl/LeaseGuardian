<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const showPwd = ref(false)

async function submit() {
  error.value = ''

  if (!form.username || !form.password) {
    error.value = '用户名和密码都要填哦～'
    return
  }

  loading.value = true
  try {
    const data = await login(form.username, form.password)
    auth.setLogin(data)

    const redirect =
        typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
            ? route.query.redirect
            : '/home'

    await router.replace(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <!-- 宽屏边缘的小云朵 -->
    <div class="deco c1" aria-hidden="true">☁️</div>
    <div class="deco c2" aria-hidden="true">☁️</div>

    <div class="wrap">
      <!-- 左：品牌门面 -->
      <section class="panel">
        <div class="p-logo" aria-hidden="true">🏠</div>
        <h1>寓见</h1>
        <p class="slogan">寓见好寓所，遇见安心</p>
        <ul class="feats">
          <li>🔧 报修一点就通</li>
          <li>📋 租约清清楚楚</li>
          <li>🌱 管家随时在线</li>
        </ul>
        <div class="scene" aria-hidden="true">
          <span class="sun">☀️</span>
          <span class="house">🏡</span>
          <span class="key">🔑</span>
        </div>
      </section>

      <!-- 右：登录卡 -->
      <form class="card" @submit.prevent="submit">
        <h2>欢迎回来 👋</h2>
        <p class="sub">登录你的小窝</p>

        <p v-if="error" class="error">😢 {{ error }}</p>

        <label>用户名
          <input v-model.trim="form.username" autocomplete="username" placeholder="请输入用户名" />
        </label>
        <label>密码
          <div class="pwd">
            <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
            />
            <span class="eye" @click="showPwd = !showPwd" :title="showPwd ? '藏起来' : '看一眼'">
              {{ showPwd ? '🙈' : '👀' }}
            </span>
          </div>
        </label>

        <button :disabled="loading">{{ loading ? '登录中…' : '登 录' }}</button>
        <p class="link">还没有账号？<router-link to="/register">去注册 →</router-link></p>
      </form>
    </div>
  </main>
</template>

<style scoped>
/* ===== 寓见 · 蜜桃焦糖主题（登录页样板房） ===== */
.auth-page {
  --peach: #ff9e7d;
  --peach-deep: #f0825f;
  --caramel: #ffc98b;
  --cream: #fdf8f2;
  --cocoa: #4a3f35;
  --warm-gray: #8a7b6e;
  --line: #f0e2d4;
  --coral: #e07a5f;

  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
      radial-gradient(600px 320px at 88% 8%, rgba(255, 201, 139, .30), transparent),
      radial-gradient(560px 300px at 6% 96%, rgba(255, 158, 125, .18), transparent),
      var(--cream);
}

/* 宽屏边缘装饰 */
.deco { position: fixed; pointer-events: none; display: none; opacity: .75; }
.c1 { top: 12vh; left: 6vw; font-size: 42px; animation: drift 13s ease-in-out infinite alternate; }
.c2 { bottom: 14vh; right: 7vw; font-size: 30px; animation: drift 10s ease-in-out infinite alternate-reverse; }
@media (min-width: 1100px) { .deco { display: block; } }

/* ===== 左右布局 ===== */
.wrap {
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 48px;
  align-items: center;
  animation: rise .55s ease both;
}
@media (max-width: 880px) {
  .wrap { grid-template-columns: 1fr; gap: 28px; }
  .panel { text-align: center; }
  .feats, .scene { display: none; }
}

/* ===== 左：品牌门面 ===== */
.panel { position: relative; }
.p-logo {
  width: 64px; height: 64px; border-radius: 20px; background: #ffe8dc;
  display: grid; place-items: center; font-size: 32px; margin-bottom: 18px;
  box-shadow: 0 8px 20px rgba(255, 158, 125, .28);
}
@media (max-width: 880px) {
  .p-logo { margin: 0 auto 12px; }
}
.panel h1 { margin: 0; font-size: 44px; letter-spacing: 4px; color: var(--cocoa); }
.slogan { margin: 10px 0 26px; font-size: 16px; color: var(--warm-gray); letter-spacing: 1px; }
.feats { list-style: none; display: flex; flex-direction: column; gap: 12px; margin: 0 0 10px; padding: 0; }
.feats li { font-size: 15px; color: var(--cocoa); background: rgba(255,255,255,.65); border: 1px solid var(--line); border-radius: 999px; padding: 8px 16px; width: fit-content; }
@media (max-width: 880px) { .feats li { margin: 0 auto; } }

.scene { position: relative; height: 120px; margin-top: 20px; }
.scene .house { position: absolute; bottom: 0; left: 20px; font-size: 64px; }
.scene .sun { position: absolute; top: 0; left: 100px; font-size: 32px; animation: spin 26s linear infinite; }
.scene .key { position: absolute; bottom: 8px; left: 120px; font-size: 26px; animation: bob 3s ease-in-out infinite; }

/* ===== 右：登录卡 ===== */
.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 34px 32px 28px;
  box-shadow: 0 16px 44px rgba(255, 158, 125, .16);
}
.card h2 { margin: 0 0 4px; font-size: 23px; color: var(--cocoa); }
.card .sub { margin: 0 0 20px; font-size: 14px; color: var(--warm-gray); }

/* 失败提示：暖珊瑚软块，不吓人 */
.error {
  margin: 0 0 14px;
  color: var(--coral);
  background: #fdf0eb;
  border: 1px solid #f8d8cb;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
}

/* 输入框 */
.card label { display: block; margin: 14px 0; font-size: 14px; font-weight: 600; color: var(--cocoa); }
.card input {
  width: 100%; margin-top: 7px;
  border: 1px solid var(--line); border-radius: 12px;
  padding: 11px 14px; font: inherit; color: var(--cocoa);
  background: #fffdf9;
  transition: border-color .2s ease, box-shadow .2s ease;
}
.card input::placeholder { color: #cdbfae; }
.card input:focus {
  outline: none;
  border-color: var(--peach);
  box-shadow: 0 0 0 4px rgba(255, 158, 125, .15);
}

/* 密码框 + 小眼睛 */
.pwd { position: relative; }
.pwd input { padding-right: 42px; }
.eye {
  position: absolute; right: 10px; top: 50%;
  transform: translateY(-28%);
  cursor: pointer; font-size: 17px; user-select: none;
  opacity: .75; transition: opacity .2s;
}
.eye:hover { opacity: 1; }

/* 登录按钮：蜜桃胶囊 */
.card button {
  width: 100%; margin-top: 10px;
  border: 0; border-radius: 999px;
  padding: 12px 14px;
  background: linear-gradient(135deg, var(--peach), #ffb26b);
  color: #fff; font-size: 16px; font-weight: 700; letter-spacing: 4px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(255, 158, 125, .35);
  transition: transform .2s ease, box-shadow .2s ease, opacity .2s ease;
}
.card button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(255, 158, 125, .45);
}
.card button:disabled { opacity: .55; cursor: not-allowed; box-shadow: none; }

/* 注册链接 */
.link { margin: 18px 0 0; text-align: center; font-size: 14px; color: var(--warm-gray); }
.link a { color: var(--peach-deep); font-weight: 600; }
.link a:hover { text-decoration: underline; text-underline-offset: 3px; }

/* 动效（轻轻的） */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(16px); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@media (prefers-reduced-motion: reduce) {
  .wrap, .deco, .scene span { animation: none; }
}
</style>
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
    <!-- 宽屏边缘装饰（emoji 由各主题 CSS 注入，HTML 保持空占位） -->
    <div class="deco c1" aria-hidden="true"></div>
    <div class="deco c2" aria-hidden="true"></div>
    <!-- cute 主题专属飘浮小心心 -->
    <div class="deco heart h1" aria-hidden="true"></div>
    <div class="deco heart h2" aria-hidden="true"></div>
    <div class="deco heart h3" aria-hidden="true"></div>
    <div class="deco heart h4" aria-hidden="true"></div>

    <!-- 右下角主题切换器（全局注册，详见 main.ts 两行接入） -->
    <ThemeSwitcher />

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
        <!-- 猫占位：cute 用贴纸图（/img/cats/sleep.webp），nature 用 emoji，simple 隐藏 -->
        <div class="cat" aria-hidden="true"></div>
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
/* ===== 寓见 · 登录页（多主题版：蜜桃奶油 / 薄荷森林 / 燕麦拿铁） =====
   所有颜色走全局 var(--token)，这里只负责布局与主题差异装饰。 */

.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
      radial-gradient(600px 320px at 88% 8%, color-mix(in srgb, var(--primary) 22%, transparent), transparent),
      radial-gradient(560px 300px at 6% 96%, color-mix(in srgb, var(--primary) 14%, transparent), transparent),
      var(--bg);
  transition: background-color .3s ease;
}

/* ===== 宽屏边缘装饰 =====
   默认（薄荷森林）：叶子；cute：云朵+气球；simple：全部隐藏。 */
.deco {
  position: fixed;
  pointer-events: none;
  display: none;
  opacity: .8;
}
.deco::before {
  display: inline-block;
  /* 贴纸白边：支持的浏览器里 emoji 会像贴纸，不支持的 plain emoji 也不亏 */
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .12));
}
.c1 { top: 12vh; left: 6vw; font-size: 42px; animation: drift 13s ease-in-out infinite alternate; }
.c2 { bottom: 14vh; right: 7vw; font-size: 32px; animation: drift 10s ease-in-out infinite alternate-reverse; }
.c1::before { content: "🍃"; }
.c2::before { content: "🌿"; }
[data-theme="cute"] .c1::before { content: "☁️"; }
[data-theme="cute"] .c2::before { content: "🎈"; font-size: 38px; }
[data-theme="simple"] .deco { display: none !important; }
@media (min-width: 1100px) { .deco { display: block; } }

/* cute 专属飘浮小心心 */
.heart { display: none; }
.heart::before { -webkit-text-stroke-width: 2px; }
.h1 { top: 20vh; left: 14vw; }
.h2 { top: 34vh; right: 11vw; }
.h3 { bottom: 26vh; left: 20vw; }
.h4 { bottom: 40vh; right: 18vw; }
.h1::before, .h3::before { content: "💖"; font-size: 20px; }
.h2::before, .h4::before { content: "⭐"; font-size: 16px; }
[data-theme="cute"].auth-page .heart,
[data-theme="cute"] .heart { display: block; animation: floaty 6s ease-in-out infinite; }
[data-theme="cute"] .h2 { animation-delay: -2s; }
[data-theme="cute"] .h3 { animation-delay: -3.5s; }
[data-theme="cute"] .h4 { animation-delay: -1s; }

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
  .feats, .scene, .cat { display: none; }
}

/* ===== 左：品牌门面 ===== */
.panel { position: relative; }
.p-logo {
  width: 64px; height: 64px; border-radius: calc(var(--radius-card) - 4px);
  background: var(--primary-tint);
  display: grid; place-items: center; font-size: 32px; margin-bottom: 18px;
  box-shadow: var(--shadow-btn);
}
@media (max-width: 880px) { .p-logo { margin: 0 auto 12px; } }
.panel h1 {
  margin: 0;
  font-size: 44px;
  letter-spacing: 4px;
  color: var(--text);
  font-family: var(--font-display);
}
.slogan { margin: 10px 0 26px; font-size: 16px; color: var(--text-secondary); letter-spacing: 1px; }
.feats { list-style: none; display: flex; flex-direction: column; gap: 12px; margin: 0; padding: 0; }
.feats li {
  font-size: 15px; color: var(--text);
  background: color-mix(in srgb, var(--surface) 72%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 8px 16px; width: fit-content;
}
@media (max-width: 880px) { .feats li { margin: 0 auto; } }

.scene { position: relative; height: 120px; margin-top: 20px; }
.scene .house { position: absolute; bottom: 0; left: 20px; font-size: 64px; }
.scene .sun { position: absolute; top: 4px; left: 104px; font-size: 30px; animation: drift 12s ease-in-out infinite alternate; }
.scene .key { position: absolute; bottom: 8px; left: 126px; font-size: 26px; animation: bob 3s ease-in-out infinite; }
[data-theme="simple"] .scene { display: none; }

/* 猫：cute 用贴纸图（无图则不可见），nature 用 emoji，simple 隐藏 */
.cat {
  position: absolute;
  right: 8%; bottom: -8px;
  width: 84px; height: 84px;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  display: none;
}
[data-theme="cute"] .cat {
  display: block;
  background-image: url('/img/cats/sleep.webp');   /* 放一张睡觉猫贴纸，没有也不报错 */
  animation: breathe 3.6s ease-in-out infinite;
}
[data-theme="cute"] .cat:hover { animation: bob .6s ease-in-out 2; }
[data-theme="nature"] .cat { display: block; }
[data-theme="nature"] .cat::before {
  content: "🐈";
  font-size: 52px;
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .10));
}
[data-theme="simple"] .cat { display: none; }

/* ===== 右：登录卡 ===== */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 34px 32px 28px;
  box-shadow: var(--shadow-card);
  transition: border-radius .3s ease, box-shadow .3s ease;
}
.card h2 {
  margin: 0 0 4px;
  font-size: 23px;
  color: var(--text);
  font-family: var(--font-display);
}
.card .sub { margin: 0 0 20px; font-size: 14px; color: var(--text-secondary); }

/* 失败提示：软块，不吓人 */
.error {
  margin: 0 0 14px;
  color: var(--error);
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
}

/* 输入框 */
.card label { display: block; margin: 14px 0; font-size: 14px; font-weight: 600; color: var(--text); }
.card input {
  width: 100%; margin-top: 7px;
  border: 1px solid var(--border);
  border-radius: calc(var(--radius-card) - 8px);
  padding: 11px 14px; font: inherit; color: var(--text);
  background: var(--bg);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.card input::placeholder { color: var(--text-tertiary); }
.card input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary) 18%, transparent);
}

/* 密码框 + 小眼睛（修掉了原来的 translateY 魔法数字） */
.pwd { position: relative; }
.pwd input { padding-right: 42px; }
.eye {
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%);
  margin-top: 3px;   /* input 有 margin-top:7px，补半值让眼睛对准输入框中线 */
  cursor: pointer; font-size: 17px; user-select: none;
  opacity: .75; transition: opacity .2s;
}
.eye:hover { opacity: 1; }

/* 登录按钮：主题胶囊 */
.card button {
  width: 100%; margin-top: 10px;
  border: 0;
  border-radius: var(--radius-pill);
  padding: 12px 14px;
  background: var(--grad-primary);
  color: var(--on-primary);
  font-size: 16px; font-weight: 700; letter-spacing: 4px;
  font-family: var(--font-display);
  cursor: pointer;
  box-shadow: var(--shadow-btn);
  transition: transform .2s ease, box-shadow .2s ease, opacity .2s ease;
}
.card button:hover:not(:disabled) { transform: translateY(-2px); }
.card button:active:not(:disabled) { transform: scale(.97); }
.card button:disabled { opacity: .55; cursor: not-allowed; box-shadow: none; }

/* 注册链接 */
.link { margin: 18px 0 0; text-align: center; font-size: 14px; color: var(--text-secondary); }
.link a { color: var(--primary-deep); font-weight: 600; }
.link a:hover { text-decoration: underline; text-underline-offset: 3px; }

/* ===== 动效（轻轻的） ===== */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(16px); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@keyframes floaty {
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50% { transform: translateY(-18px) rotate(5deg); }
}
@media (prefers-reduced-motion: reduce) {
  .wrap, .deco, .scene span, .cat { animation: none !important; }
}
</style>
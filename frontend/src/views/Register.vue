<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '@/api/auth'

const router = useRouter()
const form = reactive({ username: '', password: '', room_no: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')
const showPwd = ref(false)

async function submit() {
  error.value = ''; success.value = ''
  if (!form.username || !form.password) { error.value = '用户名和密码都要填哦～'; return }
  if (!/^\d{3}$/.test(form.room_no)) { error.value = '房间号要 3 位数字哦，比如 302 🚪'; return }
  loading.value = true
  try {
    const data = await register(form.username, form.password, form.room_no)
    success.value = `🎉 ${data.message}：房间 ${data.room_no}，月租 ${data.monthly_rent}，押金 ${data.deposit}`
    setTimeout(() => router.push('/login'), 1500)   /* 从 800ms 调到 1500ms，让好消息多看一眼 */
  } catch (e) {
    error.value = e instanceof Error ? e.message : '注册失败，请稍后再试'
  } finally { loading.value = false }
}
</script>

<template>
  <main class="auth-page">
    <!-- 宽屏边缘装饰（emoji 由各主题 CSS 注入，HTML 保持空占位） -->
    <div class="deco b1" aria-hidden="true"></div>
    <div class="deco b2" aria-hidden="true"></div>
    <!-- cute 主题专属飘浮小心心 -->
    <div class="deco heart h1" aria-hidden="true"></div>
    <div class="deco heart h2" aria-hidden="true"></div>
    <div class="deco heart h3" aria-hidden="true"></div>
    <div class="deco heart h4" aria-hidden="true"></div>

    <!-- 底部小船主题切换器（全局注册） -->
    <ThemeSwitcher />

    <div class="wrap">
      <!-- 左：搬家门面 -->
      <section class="panel">
        <div class="p-logo" aria-hidden="true">📦</div>
        <h1>遇见</h1>
        <p class="slogan">搬新家啦，遇见新的开始</p>
        <ul class="feats">
          <li>🚪 选个心仪的房号</li>
          <li>🧳 拎包就能入住</li>
          <li>🌱 管家全程陪着你</li>
        </ul>
        <div class="scene" aria-hidden="true">
          <span class="house">🏡</span>
          <span class="box">📦</span>
          <span class="balloon">🎈</span>
        </div>
        <!-- 猫占位：cute 用挥手的猫（/img/cats/wave.webp），nature 用 emoji，simple 隐藏 -->
        <div class="cat" aria-hidden="true"></div>
      </section>

      <!-- 右：注册卡 -->
      <form class="card" @submit.prevent="submit">
        <h2>欢迎入住 🎉</h2>
        <p class="sub">注册你的专属小窝</p>

        <p v-if="error" class="error">😢 {{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>

        <label>用户名
          <input v-model.trim="form.username" autocomplete="username" placeholder="给自己起个名字吧" />
        </label>
        <label>密码
          <div class="pwd">
            <input
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="设一个记得住的密码"
            />
            <span class="eye" @click="showPwd = !showPwd" :title="showPwd ? '藏起来' : '看一眼'">
              {{ showPwd ? '🙈' : '👀' }}
            </span>
          </div>
        </label>
        <label>你的房号
          <input v-model.trim="form.room_no" maxlength="3" placeholder="例如 302 🚪" inputmode="numeric" />
        </label>

        <button :disabled="loading">{{ loading ? '办理中…' : '注 册 入 住' }}</button>
        <p class="link">已有账号？<router-link to="/login">去登录 →</router-link></p>
      </form>
    </div>
  </main>
</template>

<style scoped>
/* ===== 寓见 · 注册页（多主题版：蜜桃奶油 / 薄荷森林 / 燕麦拿铁） ===== */

.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
      radial-gradient(600px 320px at 90% 10%, color-mix(in srgb, var(--primary) 22%, transparent), transparent),
      radial-gradient(560px 300px at 4% 94%, color-mix(in srgb, var(--primary) 14%, transparent), transparent),
      var(--bg);
  transition: background-color .3s ease;
}

/* ===== 宽屏边缘装饰 =====
   默认（薄荷森林）：叶子；cute：气球+云朵；simple：全部隐藏。 */
.deco {
  position: fixed;
  pointer-events: none;
  display: none;
  opacity: .8;
}
.deco::before {
  display: inline-block;
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .12));
}
.b1 { top: 16vh; right: 6vw; font-size: 36px; animation: bob 4s ease-in-out infinite; }
.b2 { bottom: 12vh; left: 5vw; font-size: 40px; animation: drift 12s ease-in-out infinite alternate; }
.b1::before { content: "🍃"; }
.b2::before { content: "🌿"; }
[data-theme="cute"] .b1::before { content: "🎈"; font-size: 40px; }
[data-theme="cute"] .b2::before { content: "☁️"; }
[data-theme="simple"] .deco { display: none !important; }
@media (min-width: 1100px) { .deco { display: block; } }

/* cute 专属飘浮小心心 */
.heart { display: none; }
.heart::before { -webkit-text-stroke-width: 2px; }
.h1 { top: 22vh; left: 12vw; }
.h2 { top: 36vh; right: 10vw; }
.h3 { bottom: 24vh; left: 18vw; }
.h4 { bottom: 38vh; right: 16vw; }
.h1::before, .h3::before { content: "💖"; font-size: 20px; }
.h2::before, .h4::before { content: "⭐"; font-size: 16px; }
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

/* ===== 左：搬家门面 ===== */
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
.scene .box { position: absolute; bottom: 4px; left: 104px; font-size: 34px; animation: bob 3.4s ease-in-out infinite; }
.scene .balloon { position: absolute; top: -6px; left: 152px; font-size: 28px; animation: floaty 4.2s ease-in-out infinite; }
[data-theme="simple"] .scene { display: none; }

/* 猫：cute 用挥手贴纸图（无图则不可见），nature 用 emoji，simple 隐藏 */
.cat {
  position: absolute;
  right: 6%; bottom: -8px;
  width: 84px; height: 84px;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  display: none;
}
[data-theme="cute"] .cat {
  display: block;
  background-image: url('/img/cats/wave.webp');   /* 搬新家，猫在挥手；没有图则自动不显示 */
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

/* ===== 右：注册卡 ===== */
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

/* 提示块：失败珊瑚软块 / 成功抹茶软块（吃语义变量，三主题统一换肤） */
.error {
  margin: 0 0 12px;
  color: var(--error);
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
}
.success {
  margin: 0 0 12px;
  color: var(--success);
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
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

/* 密码框 + 小眼睛 */
.pwd { position: relative; }
.pwd input { padding-right: 42px; }
.eye {
  position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%);
  margin-top: 3px;
  cursor: pointer; font-size: 17px; user-select: none;
  opacity: .75; transition: opacity .2s;
}
.eye:hover { opacity: 1; }

/* 按钮：主题胶囊 */
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

/* 登录链接 */
.link { margin: 18px 0 0; text-align: center; font-size: 14px; color: var(--text-secondary); }
.link a { color: var(--primary-deep); font-weight: 600; }
.link a:hover { text-decoration: underline; text-underline-offset: 3px; }

/* ===== 动效（轻轻的） ===== */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(16px); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@keyframes floaty {
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50% { transform: translateY(-18px) rotate(5deg); }
}
@media (prefers-reduced-motion: reduce) {
  .wrap, .deco, .scene span, .cat { animation: none !important; }
}
</style>
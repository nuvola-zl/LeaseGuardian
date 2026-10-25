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
    <!-- 宽屏边缘的小装饰 -->
    <div class="deco b1" aria-hidden="true">🎈</div>
    <div class="deco b2" aria-hidden="true">☁️</div>

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
/* ===== 遇见 · 蜜桃焦糖主题（注册页样板房） ===== */
.auth-page {
  --peach: #ff9e7d;
  --peach-deep: #f0825f;
  --caramel: #ffc98b;
  --cream: #fdf8f2;
  --cocoa: #4a3f35;
  --warm-gray: #8a7b6e;
  --line: #f0e2d4;
  --coral: #e07a5f;
  --matcha: #6e8f4e;

  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
      radial-gradient(600px 320px at 90% 10%, rgba(255, 201, 139, .30), transparent),
      radial-gradient(560px 300px at 4% 94%, rgba(255, 158, 125, .18), transparent),
      var(--cream);
}

/* 宽屏边缘装饰 */
.deco { position: fixed; pointer-events: none; display: none; }
.b1 { top: 16vh; right: 6vw; font-size: 34px; animation: bob 4s ease-in-out infinite; }
.b2 { bottom: 12vh; left: 5vw; font-size: 38px; opacity: .75; animation: drift 12s ease-in-out infinite alternate; }
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

/* ===== 左：搬家门面 ===== */
.panel { position: relative; }
.p-logo {
  width: 64px; height: 64px; border-radius: 20px; background: #f1f6ea;
  display: grid; place-items: center; font-size: 32px; margin-bottom: 18px;
  box-shadow: 0 8px 20px rgba(143, 174, 107, .28);
}
@media (max-width: 880px) { .p-logo { margin: 0 auto 12px; } }
.panel h1 { margin: 0; font-size: 44px; letter-spacing: 4px; color: var(--cocoa); }
.slogan { margin: 10px 0 26px; font-size: 16px; color: var(--warm-gray); letter-spacing: 1px; }
.feats { list-style: none; display: flex; flex-direction: column; gap: 12px; margin: 0; padding: 0; }
.feats li { font-size: 15px; color: var(--cocoa); background: rgba(255,255,255,.65); border: 1px solid var(--line); border-radius: 999px; padding: 8px 16px; width: fit-content; }
@media (max-width: 880px) { .feats li { margin: 0 auto; } }

.scene { position: relative; height: 120px; margin-top: 20px; }
.scene .house { position: absolute; bottom: 0; left: 20px; font-size: 64px; }
.scene .box { position: absolute; bottom: 4px; left: 104px; font-size: 34px; animation: bob 3.4s ease-in-out infinite; }
.scene .balloon { position: absolute; top: -6px; left: 152px; font-size: 28px; animation: bob 4.2s ease-in-out infinite reverse; }

/* ===== 右：注册卡 ===== */
.card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 34px 32px 28px;
  box-shadow: 0 16px 44px rgba(255, 158, 125, .16);
}
.card h2 { margin: 0 0 4px; font-size: 23px; color: var(--cocoa); }
.card .sub { margin: 0 0 20px; font-size: 14px; color: var(--warm-gray); }

/* 提示块：失败暖珊瑚 / 成功抹茶绿 */
.error {
  margin: 0 0 12px;
  color: var(--coral);
  background: #fdf0eb;
  border: 1px solid #f8d8cb;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
}
.success {
  margin: 0 0 12px;
  color: var(--matcha);
  background: #f3f8ec;
  border: 1px solid #dcebc8;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
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

/* 按钮：蜜桃胶囊 */
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

/* 登录链接 */
.link { margin: 18px 0 0; text-align: center; font-size: 14px; color: var(--warm-gray); }
.link a { color: var(--peach-deep); font-weight: 600; }
.link a:hover { text-decoration: underline; text-underline-offset: 3px; }

/* 动效（轻轻的） */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(16px); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@media (prefers-reduced-motion: reduce) {
  .wrap, .deco, .scene span { animation: none; }
}
</style>
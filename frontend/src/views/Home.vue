<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

/* ===== 管家小贴士（轮换） ===== */
const TIPS = [
  '下水道每月浇一次热水，不容易堵哦～',
  '换灯泡前先断电，安全第一 💡',
  '梅雨季记得开窗通风，被子不潮 🌿',
  '电暖器睡前关掉，暖和又安心',
  '发现墙皮起泡？拍照发给遇见管家 📷',
]
const tip = ref(TIPS[0])
let timer: number | undefined
let idx = 0
onMounted(() => {
  timer = window.setInterval(() => {
    idx = (idx + 1) % TIPS.length
    tip.value = TIPS[idx]
  }, 5000)
})
onUnmounted(() => clearInterval(timer))

/* ===== 快捷报修入口 ===== */
const QUICK = [
  { icon: '🚰', label: '水龙头' },
  { icon: '💡', label: '电灯' },
  { icon: '🚪', label: '门锁' },
  { icon: '🛁', label: '热水器' },
  { icon: '🪟', label: '门窗' },
  { icon: '📦', label: '其他' },
]
</script>

<template>
  <main class="home-page">
    <!-- 宽屏装饰（emoji 由各主题 CSS 注入，HTML 保持空占位） -->
    <div class="deco cloud" aria-hidden="true"></div>
    <div class="deco cat" aria-hidden="true"><span class="zzz" aria-hidden="true"></span></div>
    <!-- cute 专属飘浮小心心 -->
    <div class="deco heart h1" aria-hidden="true"></div>
    <div class="deco heart h2" aria-hidden="true"></div>
    <div class="deco heart h3" aria-hidden="true"></div>

    <!-- 底部小船主题切换器（全局注册） -->
    <ThemeSwitcher />

    <header class="brand">
      <div class="logo" aria-hidden="true">🏠</div>
      <div class="brand-text">
        <h1>寓见</h1>
        <p class="en">LeaseGuardian · 你的租住小管家</p>
      </div>
    </header>

    <!-- 欢迎横幅：进门第一眼 -->
    <section class="hero">
      <div class="hero-text">
        <p class="hi">欢迎回家 👋</p>
        <h2>302 的小窝</h2>
        <p class="hero-sub">今天也要住得舒舒服服～</p>
      </div>
      <div class="scene" aria-hidden="true">
        <span class="sun"></span>
        <span class="cloud2"></span>
        <span class="house"></span>
      </div>
    </section>

    <div class="layout">
      <!-- 左：主功能 -->
      <section class="main-col">
        <section class="grid">
          <router-link class="card repair" to="/repair">
            <div class="icon" aria-hidden="true">🔧</div>
            <div class="body">
              <h2>报修 / 工单</h2>
              <p>报修建单、查询工单、维修责任咨询、维修价格咨询</p>
            </div>
            <span class="arrow" aria-hidden="true">→</span>
          </router-link>

          <router-link class="card lease" to="/lease">
            <div class="icon" aria-hidden="true">🔑</div>
            <div class="body">
              <h2>租约 / 退租 / 结算</h2>
              <p>退租发起、搬离日期、损坏登记、结算确认</p>
            </div>
            <span class="arrow" aria-hidden="true">→</span>
          </router-link>
        </section>

        <!-- 快捷报修：一键直达 -->
        <section class="quick">
          <h3>⚡ 快捷报修</h3>
          <div class="chips">
            <!-- TODO: 接后端后可带参数跳转，如 /repair?item=水龙头 -->
            <router-link v-for="q in QUICK" :key="q.label" class="chip" to="/repair">
              <span aria-hidden="true">{{ q.icon }}</span>{{ q.label }}
            </router-link>
          </div>
        </section>
      </section>

      <!-- 右：小部件栏 -->
      <aside class="side-col">
        <!-- TODO: 租约数据接后端后替换 -->
        <div class="widget">
          <h3>📅 租约小提醒</h3>
          <p class="days">距离交租还有 <b>12</b> 天</p>
          <div class="bar"><i style="width: 60%"></i></div>
          <p class="mini">本月租费 ¥1,800 · 11月1日截止</p>
        </div>

        <div class="widget tip-widget">
          <h3>🌱 管家小贴士</h3>
          <p class="tip-text" :key="tip">{{ tip }}</p>
        </div>
      </aside>
    </div>

    <p class="foot">寓见 · 遇见好寓所 🍑</p>
  </main>
</template>

<style scoped>
/* ===== 寓见 · 首页（多主题版：蜜桃奶油 / 薄荷森林 / 燕麦拿铁） =====
   布局骨架：品牌头 → 欢迎横幅 → 左功能右部件 → 页脚。
   所有颜色走全局 var(--token)，装饰 emoji 由主题 CSS 注入。 */

.home-page {
  position: relative;
  min-height: 100vh;
  background:
      radial-gradient(600px 300px at 85% -5%, color-mix(in srgb, var(--primary) 16%, transparent), transparent),
      radial-gradient(520px 280px at 0% 105%, color-mix(in srgb, var(--primary) 10%, transparent), transparent),
      var(--bg);
  background-attachment: fixed;

  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 20px 96px;   /* 底部留白给小船 */
}

/* ===== 宽屏边缘装饰 =====
   默认（薄荷森林）：叶子 + 猫；cute：云朵 + 猫；simple：全隐藏 */
.deco {
  position: fixed;
  pointer-events: none;
  z-index: 0;
  display: none;
}
.deco::before {
  display: inline-block;
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .12));
}
.cloud { top: 90px; left: 4vw; font-size: 44px; animation: drift 14s ease-in-out infinite alternate; }
.cloud::before { content: "🍃"; }
.cat { bottom: 96px; right: 5vw; font-size: 46px; animation: breathe 3.5s ease-in-out infinite; }
.cat::before { content: "🐈"; }
[data-theme="cute"] .cloud::before { content: "☁️"; }
[data-theme="cute"] .cat::before { content: "🐱"; }
[data-theme="simple"] .deco { display: none !important; }
@media (min-width: 1200px) { .deco { display: block; } }

/* 猫的 zzz（simple 主题随猫一起隐藏） */
.zzz { position: absolute; top: -12px; right: -6px; font-size: 16px; color: var(--text-tertiary); }
.zzz::before { content: "z"; display: inline-block; animation: zfloat 2.4s ease-in-out infinite; }

/* cute 专属飘浮小心心（内容页密，少放几个） */
.heart { display: none; }
.heart::before { -webkit-text-stroke-width: 2px; }
.h1 { top: 24vh; left: 10vw; }
.h2 { top: 44vh; right: 8vw; }
.h3 { bottom: 30vh; left: 14vw; }
.h1::before { content: "💖"; font-size: 20px; }
.h2::before, .h3::before { content: "⭐"; font-size: 15px; }
[data-theme="cute"] .heart { display: block; animation: floaty 6s ease-in-out infinite; }
[data-theme="cute"] .h2 { animation-delay: -2.4s; }
[data-theme="cute"] .h3 { animation-delay: -1.2s; }

/* ===== 品牌头 ===== */
.brand { display: flex; align-items: center; gap: 14px; margin-bottom: 22px; animation: rise .5s ease both; }
.logo {
  width: 56px; height: 56px; border-radius: calc(var(--radius-card) - 4px);
  background: var(--primary-tint);
  display: grid; place-items: center; font-size: 28px;
  box-shadow: var(--shadow-btn);
}
.brand h1 {
  margin: 0;
  font-size: 32px;
  letter-spacing: 2px;
  color: var(--text);
  font-family: var(--font-display);
}
.en { margin: 2px 0 0; font-size: 13px; color: var(--text-secondary); }

/* ===== 欢迎横幅 ===== */
.hero {
  position: relative;
  display: flex; justify-content: space-between; align-items: center; gap: 20px;
  padding: 26px 32px;
  border-radius: var(--radius-card);
  margin-bottom: 22px;
  background: linear-gradient(120deg,
  var(--primary-tint),
  color-mix(in srgb, var(--surface) 82%, var(--bg)));
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  animation: rise .55s ease .06s both;
  transition: border-radius .3s ease;
}
.hi { margin: 0 0 4px; font-size: 14px; color: var(--text-secondary); }
.hero h2 {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--text);
  font-family: var(--font-display);
}
.hero-sub { margin: 0; font-size: 15px; color: var(--text-secondary); }

/* 横幅里的小场景（装饰，主题注入） */
.scene { position: relative; width: 170px; height: 100px; flex-shrink: 0; }
.scene .house { position: absolute; bottom: 0; right: 12px; font-size: 58px; }
.scene .house::before { content: "🏡"; }
.scene .sun { position: absolute; top: 0; right: 0; font-size: 28px; animation: drift 12s ease-in-out infinite alternate; }
.scene .sun::before { content: "☀️"; }
.scene .cloud2 { position: absolute; top: 14px; left: 6px; font-size: 26px; opacity: .9; animation: drift 9s ease-in-out infinite alternate-reverse; }
.scene .cloud2::before { content: "🍃"; }
[data-theme="cute"] .scene .cloud2::before { content: "☁️"; }
[data-theme="simple"] .scene { display: none; }

/* ===== 主布局：左主右副 ===== */
.layout {
  position: relative;
  z-index: 1;
  display: grid; grid-template-columns: 1fr 300px; gap: 18px;
  animation: rise .55s ease .14s both;
}
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

/* ===== 主功能卡 ===== */
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; }
.card {
  display: flex; align-items: center; gap: 16px;
  padding: 22px 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease,
  border-radius .3s ease;
}
.card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--primary) 40%, var(--border));
  box-shadow: var(--shadow-btn);
}
.card:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--primary) 45%, transparent);
  outline-offset: 3px;
}
.icon {
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--primary-tint);
  display: grid; place-items: center; font-size: 25px; flex-shrink: 0;
  transition: transform .25s cubic-bezier(.34, 1.56, .64, 1);
}
.card.repair:hover .icon { transform: scale(1.12) rotate(-10deg); }
.card.lease:hover .icon { transform: scale(1.12) rotate(10deg); }
.body { flex: 1; min-width: 0; }
.body h2 {
  margin: 0 0 6px;
  font-size: 18px;
  color: var(--text);
  font-family: var(--font-display);
}
.body p { margin: 0; font-size: 14px; line-height: 1.7; color: var(--text-secondary); }
.arrow { color: var(--text-tertiary); font-size: 20px; transition: transform .25s ease, color .25s ease; }
.card:hover .arrow { transform: translateX(4px); color: var(--primary); }

/* ===== 快捷报修 ===== */
.quick { margin-top: 18px; }
.quick h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--text);
  font-family: var(--font-display);
}
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 9px 16px;
  font-size: 14px;
  color: var(--text);
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.chip:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--primary) 45%, var(--border));
  box-shadow: var(--shadow-btn);
}

/* ===== 右侧小部件 ===== */
.side-col { display: flex; flex-direction: column; gap: 18px; }
.widget {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  box-shadow: var(--shadow-card);
  transition: border-radius .3s ease;
}
.widget h3 {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--text);
  font-family: var(--font-display);
}
.days { margin: 0 0 10px; font-size: 14px; color: var(--text-secondary); }
.days b { font-size: 24px; color: var(--primary); font-variant-numeric: tabular-nums; }
.bar { height: 8px; border-radius: 999px; background: var(--border); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: 999px; background: var(--grad-primary); }
.mini { margin: 10px 0 0; font-size: 12px; color: var(--text-tertiary); }
.tip-text { margin: 0; font-size: 14px; line-height: 1.8; color: var(--text-secondary); min-height: 44px; animation: fadein .45s ease; }

/* ===== 页脚 ===== */
.foot {
  margin: 40px 0 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
  animation: rise .5s ease .22s both;
}

/* ===== 动效（轻轻的） ===== */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(18px); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@keyframes zfloat {
  0% { opacity: 0; transform: translateY(4px); }
  40% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-8px); }
}
@keyframes floaty {
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50% { transform: translateY(-18px) rotate(5deg); }
}
@media (prefers-reduced-motion: reduce) {
  .brand, .hero, .layout, .foot { animation: none; }
  .deco, .scene span, .zzz::before { animation: none !important; }
}
</style>
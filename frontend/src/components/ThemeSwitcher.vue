<!-- src/components/ThemeSwitcher.vue
     三主题切换器 · 飘飘小船版
     底部正中漂浮的小船：三颗主题球是船上的货，船头插着当前主题的小旗，
     船底有水波，整船轻轻起伏。simple 主题下小船退化成安静的悬浮条。
     用法不变：main.ts 全局注册，模板里 <ThemeSwitcher />。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'

const { current, setTheme, themes } = useTheme()
const activeTheme = computed(() => themes.find(t => t.key === current.value) || themes[1])
</script>

<template>
  <div class="boat-wrap">
    <div class="boat-bob">
      <div class="boat" role="group" aria-label="切换主题">
        <span class="mast" aria-hidden="true"></span>
        <span class="flag" aria-hidden="true">{{ activeTheme.emoji }}</span>

        <div class="cargo">
          <button
              v-for="t in themes"
              :key="t.key"
              class="ball"
              :class="{ active: current === t.key }"
              :title="t.name"
              :aria-label="`切换到${t.name}`"
              :aria-pressed="current === t.key"
              @click="setTheme(t.key)"
          >
            {{ t.emoji }}
          </button>
        </div>

        <div class="hull" aria-hidden="true"></div>
      </div>

      <div class="waves" aria-hidden="true"><i></i><i></i><i></i></div>
    </div>

    <div class="boat-name">{{ activeTheme.name }}</div>
  </div>
</template>

<style scoped>
/* ===== 定位：底部正中，不挡右上角操作 ===== */
.boat-wrap {
  position: fixed;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  z-index: 9998;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  pointer-events: none;          /* 船身不抢鼠标，只有按钮可点 */
}

/* ===== 整船起伏 ===== */
.boat-bob {
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: bob 4s ease-in-out infinite;
}

/* ===== 船体 ===== */
.boat {
  pointer-events: auto;
  position: relative;
  display: flex;
  justify-content: center;
}

/* 船头小旗 + 桅杆 */
.mast {
  position: absolute;
  left: 14px; bottom: 24px;
  width: 2px; height: 24px;
  background: color-mix(in srgb, var(--text) 35%, transparent);
  border-radius: 2px;
}
.flag {
  position: absolute;
  left: 8px; bottom: 44px;
  font-size: 18px;
  transform-origin: bottom right;
  animation: flutter 2.8s ease-in-out infinite;
}

/* 三颗主题球：坐在船沿上的货 */
.cargo {
  position: absolute;
  bottom: 14px;
  display: flex;
  gap: 10px;
}
.ball {
  width: 38px; height: 38px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: var(--surface);
  display: grid; place-items: center;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(0, 0, 0, .10);
  transition: transform .25s cubic-bezier(.34, 1.56, .64, 1),
  border-color .2s ease, box-shadow .2s ease;
}
.ball:hover { transform: translateY(-6px) scale(1.1); }
.ball.active {
  transform: translateY(-9px);
  border-color: var(--primary);
  box-shadow:
      0 0 0 4px color-mix(in srgb, var(--primary) 25%, transparent),
      0 8px 16px rgba(0, 0, 0, .14);
}

/* 船身：上平下圆的木船轮廓，吃主题色 */
.hull {
  width: 172px; height: 30px;
  background: linear-gradient(180deg,
  color-mix(in srgb, var(--primary) 88%, #fff),
  var(--primary-deep));
  border-radius: 10px 10px 48px 48px;
  box-shadow:
      inset 0 -6px 0 rgba(0, 0, 0, .10),
      var(--shadow-btn);
}

/* ===== 水波 ===== */
.waves { display: flex; gap: 10px; margin-top: 4px; }
.waves i {
  width: 28px; height: 7px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 32%, transparent);
  animation: wave 2.6s ease-in-out infinite;
}
.waves i:nth-child(2) { animation-delay: .35s; }
.waves i:nth-child(3) { animation-delay: .7s; }

/* ===== 当前主题名牌 ===== */
.boat-name {
  pointer-events: none;
  font-size: 12px;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  border: 1px solid var(--border);
  padding: 3px 12px;
  border-radius: 999px;
  backdrop-filter: blur(6px);
}

/* ===== simple：小船退化成安静悬浮条 ===== */
[data-theme="simple"] .mast,
[data-theme="simple"] .flag,
[data-theme="simple"] .waves { display: none; }
[data-theme="simple"] .boat-bob { animation: none; }
[data-theme="simple"] .hull {
  height: 44px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  box-shadow: var(--shadow-card);
}
[data-theme="simple"] .cargo { bottom: 3px; }
[data-theme="simple"] .ball {
  width: 34px; height: 34px;
  border-color: transparent;
  box-shadow: none;
  background: transparent;
}
[data-theme="simple"] .ball.active {
  background: var(--primary-tint);
  transform: none;
  box-shadow: none;
}
[data-theme="simple"] .ball:hover { transform: none; background: var(--primary-tint); }

/* ===== 小屏缩小 ===== */
@media (max-width: 560px) {
  .boat-bob { scale: .85; }
}

/* ===== 动效收敛 ===== */
@keyframes bob {
  0%, 100% { transform: translateY(0) rotate(-1.2deg); }
  50% { transform: translateY(-7px) rotate(1.2deg); }
}
@keyframes flutter {
  0%, 100% { transform: rotate(-6deg); }
  50% { transform: rotate(8deg); }
}
@keyframes wave {
  0%, 100% { transform: scaleX(.85); opacity: .45; }
  50% { transform: scaleX(1.25); opacity: .85; }
}
@media (prefers-reduced-motion: reduce) {
  .boat-bob, .flag, .waves i { animation: none !important; }
}
</style>
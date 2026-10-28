<!-- src/components/AppToast.vue
     用法：在 App.vue 里挂一次 <AppToast />，之后任何页面 useToast().success('搞定啦')
     v2：颜色全部走 --success / --error / --info 语义变量，三主题自动跟肤；
     图标与入场动效按主题分性格（蜜桃奶油弹一下，燕麦拿铁安静淡入）。 -->
<script setup lang="ts">
import { computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { useTheme } from '@/composables/useTheme'

const { items } = useToast()
const { current } = useTheme()

/* 每个主题的提示图标：蜜桃奶油用桃子，薄荷森林用新芽，燕麦拿铁用极简符号 */
const ICONS = computed<Record<string, string>>(() => {
  if (current.value === 'cute') return { success: '🍑', error: '😢', info: '💡' }
  if (current.value === 'simple') return { success: '✓', error: '✕', info: 'i' }
  return { success: '🌱', error: '😢', info: '💡' }
})
</script>

<template>
  <Teleport to="body">
    <div class="toast-wrap" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in items" :key="t.id" class="toast" :class="t.type">
          <span class="t-icon" aria-hidden="true">{{ ICONS[t.type] }}</span>
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
/* 顶部居中悬浮，叠成一列，不挡操作 */
.toast-wrap {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  z-index: 9999;
  pointer-events: none;   /* 只负责打招呼，不抢鼠标 */
}

/* 胶囊本体：基础面用主题变量 */
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 80vw;
  padding: 11px 18px;
  border-radius: 999px;
  font-size: 14px;
  line-height: 1.5;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  box-shadow: var(--shadow-card);
}

/* 三种语义色：全部来自主题 token，切主题自动换装 */
.toast.success { color: var(--success);        background: var(--success-bg);        border-color: var(--success-border); }
.toast.error   { color: var(--error);          background: var(--error-bg);          border-color: var(--error-border); }
.toast.info    { color: var(--info);           background: var(--info-bg);           border-color: var(--info-border); }

/* 蜜桃奶油：弹一下再停住（软糖落地） */
[data-theme="cute"] .toast { animation: pop .35s cubic-bezier(.34, 1.56, .64, 1); }
@keyframes pop {
  from { opacity: 0; transform: translateY(-12px) scale(.92); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* 燕麦拿铁：安静地淡入，不弹 */
[data-theme="simple"] .toast { animation: fade .25s ease; }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }

/* 滑入滑出 */
.toast-enter-active, .toast-leave-active { transition: all .3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-14px); }
.toast-leave-to   { opacity: 0; transform: translateY(-8px); }
.toast-move { transition: transform .3s ease; }

@media (prefers-reduced-motion: reduce) {
  .toast, .toast-enter-active, .toast-leave-active { animation: none; transition: none; }
}
</style>
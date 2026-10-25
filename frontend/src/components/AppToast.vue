<!-- src/components/AppToast.vue
     用法：在 App.vue 里挂一次 <AppToast />，之后任何页面 useToast().success('搞定啦 🍑') -->
<script setup lang="ts">
import { useToast } from '@/composables/useToast.ts'
const { items } = useToast()

const ICONS: Record<string, string> = {
  success: '🍑',
  error: '😢',
  info: '💡',
}
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

/* 胶囊本体 */
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 80vw;
  padding: 11px 18px;
  border-radius: 999px;
  font-size: 14px;
  line-height: 1.5;
  background: #fff;
  border: 1px solid var(--line, #f0e2d4);
  box-shadow: 0 10px 30px rgba(74, 63, 53, .12);
}

/* 三种表情：成功抹茶 / 失败珊瑚 / 提示焦糖 */
.toast.success { color: #6e8f4e; background: #f3f8ec; border-color: #dcebc8; }
.toast.error   { color: #e07a5f; background: #fdf0eb; border-color: #f8d8cb; }
.toast.info    { color: #a06a1f; background: #fff6e8; border-color: #f5e3c2; }

/* 轻轻的滑入滑出 */
.toast-enter-active, .toast-leave-active { transition: all .3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-14px); }
.toast-leave-to   { opacity: 0; transform: translateY(-8px); }
.toast-move { transition: transform .3s ease; }
</style>
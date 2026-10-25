// src/composables/useToast.ts
// 遇见 · 迷你 toast —— 全局状态 + 一行调用的组合式函数
import { reactive } from 'vue'

export interface ToastItem {
    id: number
    type: 'success' | 'error' | 'info'
    message: string
}

/* 模块级响应式状态：任何页面 push，AppToast.vue 自动出现 */
const state = reactive<{ items: ToastItem[] }>({ items: [] })
let seq = 0

function push(type: ToastItem['type'], message: string, duration = 2500) {
    const id = ++seq
    state.items.push({ id, type, message })
    setTimeout(() => {
        const i = state.items.findIndex(t => t.id === id)
        if (i > -1) state.items.splice(i, 1)
    }, duration)
}

export function useToast() {
    return {
        items: state.items,
        success: (msg: string, duration?: number) => push('success', msg, duration),
        error: (msg: string, duration?: number) => push('error', msg, duration),
        info: (msg: string, duration?: number) => push('info', msg, duration),
    }
}
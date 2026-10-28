// src/composables/useToast.ts
// 寓见 · 迷你 toast —— 全局状态 + 一行调用的组合式函数
// v2：蜜桃奶油主题下给成功/提示消息加撒娇尾音（错误消息保持严肃，所有主题不变）
import { reactive } from 'vue'
import { useTheme } from './useTheme'

export interface ToastItem {
    id: number
    type: 'success' | 'error' | 'info'
    message: string
}

/* 模块级响应式状态：任何页面 push，AppToast.vue 自动出现 */
const state = reactive<{ items: ToastItem[] }>({ items: [] })
let seq = 0

/** 撒娇尾音：仅 cute 主题 + 成功/提示 + 原文没收尾语气词时才加 */
function cutify(message: string, type: ToastItem['type']): string {
    if (type === 'error') return message
    if (useTheme().current.value !== 'cute') return message
    if (/[～~！!？?。…啦呀哦呢]$/.test(message)) return message
    return `${message}啦～`
}

function push(type: ToastItem['type'], message: string, duration = 2500) {
    const id = ++seq
    state.items.push({ id, type, message: cutify(message, type) })
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
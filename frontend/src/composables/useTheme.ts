// src/composables/useTheme.ts
// 寓见 · 三主题切换：挂载前 initTheme() 防闪，之后 setTheme() 随时切。
import { ref } from 'vue'

export type ThemeKey = 'cute' | 'nature' | 'simple'

export const THEME_LIST: { key: ThemeKey; name: string; emoji: string }[] = [
    { key: 'cute',   name: '蜜桃奶油', emoji: '🍑' },
    { key: 'nature', name: '薄荷森林', emoji: '🌿' },
    { key: 'simple', name: '燕麦拿铁', emoji: '⬜' },
]

const STORAGE_KEY = 'lg_theme'

function getInitialTheme(): ThemeKey {
    try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved === 'cute' || saved === 'nature' || saved === 'simple') return saved
    } catch {
        /* localStorage 不可用时回落默认主题 */
    }
    return 'nature'
}

const current = ref<ThemeKey>(getInitialTheme())

/** 把主题写到 <html data-theme>，并同步 <meta name="theme-color">（手机地址栏） */
function applyTheme(t: ThemeKey) {
    document.documentElement.setAttribute('data-theme', t)
    const color = getComputedStyle(document.documentElement)
        .getPropertyValue('--theme-color')
        .trim()
    if (color) {
        let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
        if (!meta) {
            meta = document.createElement('meta')
            meta.name = 'theme-color'
            document.head.appendChild(meta)
        }
        meta.content = color
    }
}

/** main.ts 里、app.mount 之前调用一次 */
export function initTheme() {
    applyTheme(current.value)
}

export function setTheme(t: ThemeKey) {
    current.value = t
    try {
        localStorage.setItem(STORAGE_KEY, t)
    } catch {
        /* 存不进去也不影响使用 */
    }
    applyTheme(t)
}

export function useTheme() {
    return { current, setTheme, themes: THEME_LIST }
}
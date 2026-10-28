import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ThemeSwitcher from './components/ThemeSwitcher.vue'
import { initTheme } from './composables/useTheme'
import './assets/main.css'

initTheme()   // 挂载前初始化主题（写 data-theme + localStorage），防止闪烁

createApp(App)
    .use(createPinia())
    .use(router)
    .component('ThemeSwitcher', ThemeSwitcher)   // 全局注册，任何页面 <ThemeSwitcher /> 直接用
    .mount('#app')
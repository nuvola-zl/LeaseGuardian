<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { me } from '@/api/auth'
import { fetchChatHistory, fetchChatSessions, type Scene } from '@/api/chat'
import { streamChat, type Persona } from '@/api/chatSse'
import { LOGIN_EXPIRED } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'   // ★ 新增：语气切换提示
import type { ChatSession } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()                            // ★ 新增

type PersonaKey = 'DEFAULT' | Persona
type Message = { role: 'user' | 'assistant'; content: string }

const scene = computed(() => route.meta.scene as Scene | undefined)
const title = computed(() => (route.meta.title as string | undefined) || '智能助理')
const storageKey = computed(() => `lg_chat_session_${scene.value || 'auto'}`)

/* ★ 每个语气配个小表情 */
const personaOptions: { key: PersonaKey; label: string; emoji: string }[] = [
  { key: 'DEFAULT', label: '原语气', emoji: '🍑' },
  { key: 'SWEET', label: '温柔', emoji: '🌸' },
  { key: 'SASSY', label: '毒舌', emoji: '😏' },
  { key: 'NORTHEAST', label: '东北', emoji: '🧊' },
]

const persona = ref<PersonaKey>(
    (localStorage.getItem('lg_persona') as PersonaKey) || 'DEFAULT',
)

const activePersona = computed(() =>
    persona.value === 'DEFAULT' ? undefined : persona.value,
)

function setPersona(key: PersonaKey) {
  persona.value = key
  if (key === 'DEFAULT') localStorage.removeItem('lg_persona')
  else localStorage.setItem('lg_persona', key)
}

/* ★ 语气小胶囊（下拉弹出） */
const personaOpen = ref(false)
const currentPersona = computed(() =>
    personaOptions.find(p => p.key === persona.value) || personaOptions[0]!,
)
function pickPersona(p: { key: PersonaKey; label: string; emoji: string }) {
  setPersona(p.key)
  personaOpen.value = false
  toast.info(`已切换：${p.emoji} ${p.label}模式`)
}

/* ★ 步骤小图标 */
const STEP_TEXTS: Record<string, string> = {
  understanding: '理解你的问题...',
  verifying: '核对信息...',
  querying: '查询相关数据...',
  creating: '创建 / 处理单据...',
  processing: '处理中...',
  polishing: '润色回复...',
}
const STEP_ICONS: Record<string, string> = {
  understanding: '🧠',
  verifying: '🔍',
  querying: '📊',
  creating: '📝',
  processing: '⚙️',
  polishing: '✨',
}

/* ★ 快捷问题：按场景给第一脚油门 */
const QUICK: Record<string, string[]> = {
  repair: ['厨房水龙头漏水', '卫生间的灯不亮', '门锁打不开', '查询我的工单'],
  lease: ['我想办理退租', '这个月账单是多少', '租约什么时候到期', '押金怎么退'],
  default: ['我想报修', '租约有疑问', '这个月账单', '找人工客服'],
}
const quickQuestions = computed<string[]>(() => QUICK[scene.value || ''] || QUICK.default!)
function quickSend(text: string) {
  if (sending.value) return
  input.value = text
  send()
}

const input = ref('')
const sending = ref(false)
const statusText = ref('')
const statusStep = ref('')                          // ★ 当前步骤 key
const box = ref<HTMLElement>()

const sessions = ref<ChatSession[]>([])
const sessionLoading = ref(false)
const historyLoading = ref(false)
const currentSessionId = ref<string | null>(null)
const streamingIndex = ref<number | null>(null)
const messages = ref<Message[]>([])

const welcome: Message = { role: 'assistant', content: '你好，直接描述你的问题即可。' }

/* ★ 渲染用消息列表：滤掉遗留的纯文本欢迎消息（欢迎已由卡片接管） */
const visibleMessages = computed(() =>
    messages.value.filter(
        (m, i) => !(i === 0 && m.role === 'assistant' && m.content === welcome.content),
    ),
)
/* ★ 欢迎卡：用户还没开口时显示 */
const showWelcome = computed(() => !visibleMessages.value.some(m => m.role === 'user'))

let abortController: AbortController | null = null
let flushTimer: number | undefined = undefined
let pendingText = ''

function readLocalSession(): {
  session_id?: string | number
  messages?: Message[]
} | null {
  try {
    const raw = localStorage.getItem(storageKey.value)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persistLocalSession() {
  localStorage.setItem(
      storageKey.value,
      JSON.stringify({
        session_id: currentSessionId.value,
        messages: messages.value.slice(-50),
      }),
  )
}

function clearLocalSession() {
  localStorage.removeItem(storageKey.value)
}

function mapHistory(list: { role: 'USER' | 'ASSISTANT'; content: string }[]): Message[] {
  return list.map(m => ({
    role: m.role === 'USER' ? 'user' : 'assistant',
    content: m.content,
  }))
}

function fmtTime(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function scrollBottom(smooth = true) {
  nextTick(() => {
    box.value?.scrollTo({
      top: box.value.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    })
  })
}

async function toLogin() {
  auth.logout()
  router.push('/login')
}

function push(role: 'user' | 'assistant', content: string) {
  messages.value.push({ role, content })
  persistLocalSession()
  scrollBottom()
}

function ensureAssistantBubble() {
  messages.value.push({ role: 'assistant', content: '' })
  streamingIndex.value = messages.value.length - 1
}

function startFlush() {
  stopFlush()

  flushTimer = window.setInterval(() => {
    const idx = streamingIndex.value
    if (!pendingText || idx === null || !messages.value[idx]) return

    messages.value[idx].content += pendingText
    pendingText = ''
    scrollBottom()
  }, 40)
}

function stopFlush() {
  if (flushTimer) {
    window.clearInterval(flushTimer)
    flushTimer = undefined
  }

  const idx = streamingIndex.value
  if (pendingText && idx !== null && messages.value[idx]) {
    messages.value[idx].content += pendingText
    pendingText = ''
  }
}

function cancelStream() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

function startNewSession() {
  cancelStream()
  stopFlush()

  currentSessionId.value = null
  streamingIndex.value = null
  messages.value = [welcome]
  clearLocalSession()
  scrollBottom(false)
}

async function selectSession(sessionId: string | number) {
  cancelStream()
  stopFlush()

  historyLoading.value = true
  currentSessionId.value = String(sessionId)
  persistLocalSession()

  try {
    const history = await fetchChatHistory(sessionId)
    const mapped = mapHistory(history)
    messages.value = mapped.length ? mapped : []
    persistLocalSession()
    scrollBottom(false)
  } catch (e) {
    const err = e as Error & { code?: string }

    if (err.code === LOGIN_EXPIRED) {
      return toLogin()
    }

    if (err.code === 'A00011') {
      sessions.value = sessions.value.filter(
          s => String(s.session_id) !== String(sessionId),
      )
      clearLocalSession()
      startNewSession()
      return
    }

    const local = readLocalSession()
    if (
        local?.session_id != null &&
        String(local.session_id) === String(sessionId) &&
        local.messages?.length
    ) {
      messages.value = local.messages
    } else {
      messages.value = [welcome]
    }
  } finally {
    historyLoading.value = false
  }
}

async function refreshSessions() {
  if (!scene.value) {
    messages.value = [welcome]
    return
  }

  sessionLoading.value = true
  try {
    const list = await fetchChatSessions(scene.value)
    sessions.value = list

    const local = readLocalSession()
    const localId = local?.session_id != null ? String(local.session_id) : null

    if (localId && list.some(s => String(s.session_id) === localId)) {
      await selectSession(localId)
      return
    }

    if (list.length) {
      await selectSession(list[0]!.session_id)
      return
    }

    startNewSession()
  } catch (e) {
    const err = e as Error & { code?: string }

    if (err.code === LOGIN_EXPIRED) {
      return toLogin()
    }

    const local = readLocalSession()
    if (local?.session_id) {
      currentSessionId.value = String(local.session_id)
      messages.value = local.messages?.length ? local.messages : [welcome]
    } else {
      messages.value = [welcome]
    }
  } finally {
    sessionLoading.value = false
  }
}

async function syncSessionsAfterSend() {
  if (!scene.value) return
  try {
    sessions.value = await fetchChatSessions(scene.value)
  } catch {
    // 列表刷新失败不影响当前聊天
  }
}

async function send() {
  const msg = input.value.trim()
  if (!msg || sending.value) return

  cancelStream()

  input.value = ''
  push('user', msg)

  sending.value = true
  statusText.value = '正在连接...'
  ensureAssistantBubble()
  scrollBottom(false)

  const controller = new AbortController()
  abortController = controller

  startFlush()

  try {
    const done = await streamChat({
      message: msg,
      scene: scene.value,
      sessionId: currentSessionId.value,
      persona: activePersona.value,
      signal: controller.signal,
      onStatus: step => {
        statusStep.value = step                 // ★ 记步骤
        statusText.value = STEP_TEXTS[step] || '处理中...'
      },
      onToken: text => {
        pendingText += text
      },
      onDone: () => {
        // done 由外层 await 后的返回值统一处理
      },
    })

    stopFlush()

    const idx = streamingIndex.value
    if (idx !== null && messages.value[idx]) {
      messages.value[idx].content = done.answer
    }

    if (done.session_id) {
      currentSessionId.value = String(done.session_id)
    }

    persistLocalSession()
    scrollBottom()
    void syncSessionsAfterSend()
  } catch (e) {
    stopFlush()

    const err = e as Error & { code?: string }
    const idx = streamingIndex.value

    if (controller.signal.aborted) {
      if (idx !== null && messages.value[idx] && !messages.value[idx].content) {
        messages.value[idx].content = '已取消'
        persistLocalSession()
      }
      return
    }

    if (err.code === LOGIN_EXPIRED) {
      return toLogin()
    }

    if (idx !== null && messages.value[idx]) {
      messages.value[idx].content = `请求失败：${err.message || '请稍后重试'}`
      persistLocalSession()
    }
  } finally {
    abortController = null
    sending.value = false
    statusText.value = ''
    statusStep.value = ''                       // ★ 清空步骤
    streamingIndex.value = null
    scrollBottom()
  }
}

onMounted(async () => {
  await refreshSessions()

  if (auth.me) return
  try {
    auth.setMe(await me())
  } catch {
    // /auth/me 失败不阻塞聊天
  }
})

onBeforeUnmount(() => {
  cancelStream()
  stopFlush()
})
</script>

<template>
  <main class="chat-page session-layout">
    <!-- 宽屏装饰（emoji 由各主题 CSS 注入，HTML 保持空占位） -->
    <div class="deco leaf" aria-hidden="true"></div>
    <!-- cute 专属飘浮小心心 -->
    <div class="deco heart h1" aria-hidden="true"></div>
    <div class="deco heart h2" aria-hidden="true"></div>
    <div class="deco heart h3" aria-hidden="true"></div>

    <!-- 主题小船：聊天页里挪到输入框左上方（见样式底部 :deep 覆盖），不挡输入 -->
    <ThemeSwitcher />

    <!-- ===== 左：会话栏 ===== -->
    <aside class="sessions">
      <div class="sessions-head">
        <div class="brand-mini">
          <span class="mini-logo" aria-hidden="true">🏠</span>
          <strong class="side-title">{{ title }}</strong>
        </div>
        <button class="new-session" :disabled="sending" @click="startNewSession">
          ＋ 新建
        </button>
      </div>

      <div v-if="sessionLoading" class="side-note">加载会话...</div>

      <div v-else class="session-list">
        <button
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: currentSessionId === String(s.session_id) }"
            :disabled="sending || historyLoading"
            @click="selectSession(s.session_id)"
        >
          <span class="session-title">{{ s.title || '未命名会话' }}</span>
          <span class="session-time">{{ fmtTime(s.updated_at) }}</span>
        </button>

        <div v-if="!sessions.length" class="side-note">
          暂无会话，点「＋ 新建」开始
        </div>
      </div>
    </aside>

    <!-- ===== 右：聊天主区 ===== -->
    <section class="chat-main">
      <header class="topbar">
        <div class="tb-left">
          <router-link to="/home" class="back" title="返回首页" aria-label="返回首页">←</router-link>
          <strong class="tb-title mobile-only">{{ title }}</strong>
        </div>

        <div class="tb-right">
          <!-- 语气小胶囊 -->
          <div class="persona-wrap">
            <button
                class="persona-btn"
                :disabled="sending"
                @click="personaOpen = !personaOpen"
            >
              {{ currentPersona.emoji }} {{ currentPersona.label }}
              <span class="chev" aria-hidden="true">▾</span>
            </button>

            <div v-if="personaOpen" class="pop-mask" @click="personaOpen = false"></div>
            <div v-if="personaOpen" class="persona-pop" role="menu">
              <button
                  v-for="p in personaOptions"
                  :key="p.key"
                  class="pop-item"
                  :class="{ active: persona === p.key }"
                  role="menuitem"
                  @click="pickPersona(p)"
              >
                {{ p.emoji }} {{ p.label }}
              </button>
            </div>
          </div>

          <!-- 用户信息 -->
          <div v-if="auth.me" class="user-chip" :title="`${auth.me.room_no} · ${auth.me.status}`">
            <span class="u-avatar">{{ (auth.me.username || '客').charAt(0) }}</span>
            <span class="u-name">{{ auth.me.username }}</span>
            <span class="u-room">{{ auth.me.room_no }} · {{ auth.me.status }}</span>
          </div>

          <button class="logout" @click="toLogin">退出</button>
        </div>
      </header>

      <section ref="box" class="messages">
        <!-- 欢迎卡 -->
        <div v-if="showWelcome && !sending && !historyLoading" class="welcome">
          <div class="w-mascot" aria-hidden="true"></div>
          <h2>你好呀，我是寓见管家～</h2>
          <p>水龙头坏了？租约有疑问？都可以跟我说</p>
          <div class="w-chips">
            <button
                v-for="q in quickQuestions"
                :key="q"
                class="w-chip"
                @click="quickSend(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <div v-for="(m, i) in visibleMessages" :key="i" class="msg" :class="m.role">
          <div v-if="m.role === 'assistant'" class="avatar" aria-hidden="true">🏠</div>
          <div class="bubble">
            {{ m.content }}
            <span v-if="sending && streamingIndex === i" class="caret"></span>
          </div>
        </div>

        <!-- 加载历史 -->
        <div v-if="historyLoading" class="msg assistant">
          <div class="avatar" aria-hidden="true">🏠</div>
          <div class="bubble status-card">
            <span class="s-icon" aria-hidden="true">📂</span>
            <span class="s-text">加载历史...</span>
            <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
          </div>
        </div>

        <!-- 步骤状态卡 -->
        <div v-if="sending" class="msg assistant">
          <div class="avatar" aria-hidden="true">🏠</div>
          <div class="bubble status-card">
            <span class="s-icon" aria-hidden="true">{{ STEP_ICONS[statusStep] || '⚙️' }}</span>
            <span class="s-text">{{ statusText }}</span>
            <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
          </div>
        </div>
      </section>

      <!-- 输入框旁边的小伙伴：cute 用贴纸图（睡觉/猫爪拍屏两态），nature 用 emoji，simple 隐藏 -->
      <div class="composer-cat" :data-busy="sending" aria-hidden="true"></div>

      <form class="composer" @submit.prevent="send">
        <input
            v-model="input"
            :disabled="sending"
            placeholder="输入一句话，例如：厨房水龙头漏水"
        />
        <button v-if="!sending" type="submit" class="send" :disabled="!input.trim()">
          发送 ✈
        </button>
        <button v-else type="button" class="stop" @click="cancelStream">
          ⏹ 停止
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
/* ===== 寓见 · 聊天页（多主题版：蜜桃奶油 / 薄荷森林 / 燕麦拿铁） =====
   流式逻辑零改动，本文件只负责皮肤与装饰。 */

.chat-page {
  position: relative;
}

/* ===== 一室一厅布局 ===== */
.session-layout {
  display: grid;
  grid-template-columns: 264px minmax(0, 1fr);
  max-width: 1120px;
  height: 100vh;
  margin: 0 auto;
  background:
      radial-gradient(500px 260px at 90% 0%, color-mix(in srgb, var(--primary) 14%, transparent), transparent),
      radial-gradient(460px 240px at 30% 100%, color-mix(in srgb, var(--primary) 8%, transparent), transparent),
      var(--bg);
  border-left: 1px solid var(--border);
  border-right: 1px solid var(--border);
  transition: background-color .3s ease;
}

.chat-main {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-width: 0;
}

/* ===== 宽屏装饰 =====
   默认（薄荷森林）：叶子；cute：云朵；simple：全隐藏 */
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
.leaf { top: 100px; left: 3vw; font-size: 40px; animation: drift 14s ease-in-out infinite alternate; }
.leaf::before { content: "🍃"; }
[data-theme="cute"] .leaf::before { content: "☁️"; font-size: 46px; }
[data-theme="simple"] .deco { display: none !important; }
@media (min-width: 1240px) { .deco { display: block; } }

/* cute 专属飘浮小心心 */
.heart { display: none; }
.heart::before { -webkit-text-stroke-width: 2px; }
.h1 { top: 18vh; left: 22vw; }
.h2 { top: 40vh; right: 6vw; }
.h3 { bottom: 26vh; left: 30vw; }
.h1::before { content: "💖"; font-size: 18px; }
.h2::before, .h3::before { content: "⭐"; font-size: 14px; }
[data-theme="cute"] .heart { display: block; animation: floaty 6s ease-in-out infinite; }
[data-theme="cute"] .h2 { animation-delay: -2.2s; }
[data-theme="cute"] .h3 { animation-delay: -1.1s; }

/* ===== 左：会话栏 ===== */
.sessions {
  border-right: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 78%, transparent);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sessions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
}
.brand-mini { display: flex; align-items: center; gap: 8px; min-width: 0; }
.mini-logo {
  width: 30px; height: 30px; border-radius: 10px;
  background: var(--primary-tint);
  display: grid; place-items: center; font-size: 16px; flex-shrink: 0;
}
.side-title {
  font-size: 15px;
  color: var(--text);
  font-family: var(--font-display);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.new-session {
  border: 0; border-radius: var(--radius-pill); padding: 7px 13px; flex-shrink: 0;
  background: var(--grad-primary);
  color: var(--on-primary);
  font-size: 13px; font-weight: 600; cursor: pointer;
  font-family: var(--font-display);
  box-shadow: var(--shadow-btn);
  transition: transform .2s, box-shadow .2s, opacity .2s;
}
.new-session:hover:not(:disabled) { transform: translateY(-1px); }
.new-session:active:not(:disabled) { transform: scale(.96); }
.new-session:disabled { opacity: .55; cursor: not-allowed; }

.session-list { overflow-y: auto; padding: 10px; }

.session-item {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 14px;
  padding: 10px 12px 10px 14px;
  margin-bottom: 6px;
  cursor: pointer;
  color: var(--text);
  transition: background .18s, border-color .18s, transform .18s;
}
.session-item:hover:not(:disabled) {
  background: var(--surface);
  border-color: var(--border);
  transform: translateX(2px);
}
.session-item.active {
  background: var(--surface);
  border-color: color-mix(in srgb, var(--primary) 45%, var(--border));
  box-shadow: var(--shadow-card);
}
.session-item.active::before {
  content: '';
  position: absolute;
  left: 0; top: 12px; bottom: 12px;
  width: 3px; border-radius: 3px;
  background: var(--primary);
}
.session-item:disabled { opacity: .6; cursor: not-allowed; }

.session-title {
  font-size: 14px; font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.session-item.active .session-title { color: var(--primary-deep); }
.session-time { font-size: 12px; color: var(--text-tertiary); font-variant-numeric: tabular-nums; }

.side-note {
  color: var(--text-secondary);
  padding: 20px 14px;
  font-size: 13px;
  text-align: center;
}

/* ===== 右：顶栏 ===== */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: color-mix(in srgb, var(--surface) 82%, transparent);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
.tb-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.back {
  width: 34px; height: 34px; flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 16px;
  transition: border-color .2s, color .2s, transform .2s;
}
.back:hover { border-color: var(--primary); color: var(--primary-deep); transform: translateX(-2px); }
.tb-title { font-size: 16px; color: var(--text); }
.mobile-only { display: none; }

.tb-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

/* 语气小胶囊 + 下拉 */
.persona-wrap { position: relative; }
.persona-btn {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 7px 12px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
}
.persona-btn:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--primary) 45%, var(--border));
  box-shadow: var(--shadow-btn);
}
.persona-btn:disabled { opacity: .55; cursor: not-allowed; }
.chev { font-size: 11px; color: var(--text-tertiary); }
.pop-mask { position: fixed; inset: 0; z-index: 40; }
.persona-pop {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: 50;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  padding: 6px;
  display: flex; flex-direction: column; gap: 2px;
  min-width: 148px;
  animation: pop .18s ease;
}
.pop-item {
  border: 0; background: transparent; text-align: left;
  padding: 9px 12px; border-radius: 11px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  transition: background .15s;
}
.pop-item:hover { background: var(--bg); }
.pop-item.active {
  background: var(--grad-primary);
  color: var(--on-primary);
}
@keyframes pop { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }

/* 用户信息 */
.user-chip { display: flex; align-items: center; gap: 8px; }
.u-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--grad-primary);
  color: var(--on-primary);
  font-size: 14px; font-weight: 700;
  display: grid; place-items: center; flex-shrink: 0;
}
.u-name { font-size: 14px; font-weight: 600; color: var(--text); }
.u-room { font-size: 12px; color: var(--text-tertiary); }

.logout {
  border: 0; background: transparent;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 4px;
  transition: color .2s;
}
.logout:hover { color: var(--error); }

/* ===== 消息区 ===== */
.messages {
  overflow-y: auto;
  padding: 20px 18px 8px;
  position: relative;
  z-index: 1;
}

/* 欢迎卡 */
.welcome { max-width: 460px; margin: 40px auto 0; text-align: center; animation: rise .5s ease; }
.w-mascot {
  width: 76px; height: 76px; margin: 0 auto 16px;
  border-radius: 26px;
  background: var(--surface);
  border: 1px solid var(--border);
  display: grid; place-items: center; font-size: 40px;
  box-shadow: var(--shadow-card);
  position: relative;
}
.w-mascot::before {
  content: "🏠";
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .10));
}
[data-theme="cute"] .w-mascot::before { content: "🏠"; }
.welcome h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--text);
  font-family: var(--font-display);
}
.welcome > p { margin: 0 0 20px; font-size: 14px; color: var(--text-secondary); }
.w-chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.w-chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 9px 16px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  transition: transform .2s, border-color .2s, box-shadow .2s;
}
.w-chip:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--primary) 45%, var(--border));
  box-shadow: var(--shadow-btn);
}

/* 气泡 */
.msg { display: flex; align-items: flex-start; gap: 10px; margin: 14px 0; }
.msg.user { justify-content: flex-end; }
.avatar {
  width: 36px; height: 36px; border-radius: 14px; flex-shrink: 0; margin-top: 2px;
  background: var(--primary-tint);
  border: 1px solid var(--border);
  display: grid; place-items: center; font-size: 19px;
}
.bubble {
  max-width: 76%;
  white-space: pre-wrap;
  border-radius: calc(var(--radius-card) - 4px);
  padding: 11px 15px;
  font-size: 14.5px;
  line-height: 1.65;
  word-break: break-word;
}
.msg.user .bubble {
  background: var(--grad-primary);
  color: var(--on-primary);
  border-bottom-right-radius: 6px;
  box-shadow: var(--shadow-btn);
}
.msg.assistant .bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-bottom-left-radius: 6px;
  box-shadow: var(--shadow-card);
}

/* cute：消息 duang 一下弹进来（软糖落地） */
[data-theme="cute"] .msg { animation: duang .38s cubic-bezier(.34, 1.56, .64, 1) both; }
@keyframes duang {
  from { opacity: 0; transform: translateY(14px) scale(.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* 状态卡 */
.status-card { display: inline-flex; align-items: center; gap: 8px; }
.s-icon { font-size: 16px; }
.s-text { font-size: 13px; color: var(--text-secondary); }
.dots { display: inline-flex; margin-left: 2px; }
.dots i {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--primary); margin-left: 3px;
  animation: dotb 1.2s infinite;
}
.dots i:nth-child(2) { animation-delay: .15s; }
.dots i:nth-child(3) { animation-delay: .3s; }
@keyframes dotb {
  0%, 60%, 100% { transform: translateY(0); opacity: .4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* 打字光标 */
.caret {
  display: inline-block;
  width: 2px; height: 1em; margin-left: 2px;
  background: currentColor;
  vertical-align: -0.15em;
  animation: blink 0.9s steps(2, start) infinite;
}
@keyframes blink { to { visibility: hidden; } }

/* ===== 输入区 ===== */
.composer {
  display: flex; gap: 10px;
  padding: 12px 16px 18px;
  background: linear-gradient(transparent, var(--bg) 40%);
  position: relative;
  z-index: 2;
}
.composer input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 12px 18px;
  font: inherit; font-size: 14px;
  color: var(--text);
  background: var(--surface);
  transition: border-color .2s, box-shadow .2s;
}
.composer input::placeholder { color: var(--text-tertiary); }
.composer input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary) 18%, transparent);
}
.composer input:disabled { opacity: .6; }
.composer button {
  border: 0;
  border-radius: var(--radius-pill);
  padding: 0 22px; height: 46px;
  font-size: 15px; font-weight: 700;
  font-family: var(--font-display);
  cursor: pointer;
  transition: transform .2s, box-shadow .2s, background .2s, opacity .2s;
}
.send {
  background: var(--grad-primary);
  color: var(--on-primary);
  box-shadow: var(--shadow-btn);
}
.send:hover:not(:disabled) { transform: translateY(-2px); }
.send:active:not(:disabled) { transform: scale(.96); }
.send:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
.stop {
  background: var(--surface);
  border: 1.5px solid var(--error);
  color: var(--error);
}
.stop:hover { background: var(--error-bg); }

/* ===== 输入框旁的小伙伴（猫） =====
   cute：贴纸图两态（data-busy 切换 睡觉→猫爪拍屏）；nature：emoji；simple：隐藏 */
.composer-cat {
  position: absolute;
  left: 22px; bottom: 76px;
  width: 52px; height: 52px;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  display: none;
  z-index: 3;
  pointer-events: none;
}
[data-theme="cute"] .composer-cat {
  display: block;
  background-image: url('/img/cats/sleep.webp');
  animation: breathe 3.6s ease-in-out infinite;
}
[data-theme="cute"] .composer-cat[data-busy="true"] {
  background-image: url('/img/cats/paw.webp');
  animation: bob .5s ease-in-out infinite;
}
[data-theme="nature"] .composer-cat {
  display: block;
}
[data-theme="nature"] .composer-cat::before {
  content: "🐈";
  font-size: 34px;
  -webkit-text-stroke: 3px #fff;
  paint-order: stroke fill;
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, .10));
}
[data-theme="simple"] .composer-cat { display: none; }

/* ===== 主题小船在聊天页的位置：输入框左上方，不挡输入 ===== */
.chat-page :deep(.boat-wrap) {
  left: 12px;
  right: auto;
  transform: none;
  bottom: 140px;
}
@media (max-width: 900px) {
  .chat-page :deep(.boat-wrap) { bottom: 132px; }
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .session-layout { grid-template-columns: 224px minmax(0, 1fr); }
}
@media (max-width: 760px) {
  .session-layout { grid-template-columns: 1fr; }
  .sessions { display: none; }
  .mobile-only { display: inline; }
}
@media (max-width: 720px) {
  .u-room { display: none; }
  .composer-cat { display: none !important; }   /* 小屏地方小，猫先回避 */
}
@media (max-width: 520px) {
  .u-name { display: none; }
  .logout { font-size: 12px; }
  .composer button { padding: 0 16px; }
}

/* ===== 动效收敛 ===== */
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes drift { from { transform: translateX(0); } to { transform: translateX(18px); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }
@keyframes floaty {
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50% { transform: translateY(-16px) rotate(5deg); }
}
@media (prefers-reduced-motion: reduce) {
  .welcome, .persona-pop, .dots i, .caret,
  .deco, .composer-cat, [data-theme="cute"] .msg { animation: none !important; }
}
</style>
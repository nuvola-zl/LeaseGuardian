<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ragApi } from '@/api/rag'

const files = ref<{ filename: string }[]>([])
const loading = ref(false)
const uploading = ref(false)
const deleting = ref('')
const error = ref('')
const message = ref('')
const fileInput = ref<HTMLInputElement>()

const MAX_SIZE = 5 * 1024 * 1024
const ALLOWED = ['.md', '.txt', '.pdf']

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    files.value = await ragApi.listFiles()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function upload() {
  const file = fileInput.value?.files?.[0]
  error.value = ''
  message.value = ''

  if (!file) {
    error.value = '请先选择文件'
    return
  }

  const lower = file.name.toLowerCase()
  if (!ALLOWED.some(ext => lower.endsWith(ext))) {
    error.value = '只支持 .md / .txt / .pdf'
    return
  }

  if (file.size > MAX_SIZE) {
    error.value = '文件不能超过 5MB'
    return
  }

  const exists = files.value.some(f => f.filename === file.name)
  if (exists && !confirm(`已存在 ${file.name}，覆盖？`)) {
    return
  }

  uploading.value = true
  try {
    const res = await ragApi.uploadFile(file)
    message.value = `已上传 ${res.filename}，切了 ${res.chunks} 块`
    if (fileInput.value) fileInput.value.value = ''
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

async function remove(filename: string) {
  if (!confirm(`确定删除 ${filename}？`)) return
  error.value = ''
  message.value = ''
  deleting.value = filename
  try {
    await ragApi.deleteFile(filename)
    message.value = `已删除 ${filename}`
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    deleting.value = ''
  }
}

onMounted(refresh)
</script>

<template>
  <main class="admin-page">
    <!-- 主题小船（全局注册） -->
    <ThemeSwitcher />

    <header class="page-head">
      <div class="ph-icon" aria-hidden="true">📚</div>
      <div class="ph-text">
        <h1>知识库文件管理</h1>
        <p>管理智能助理的参考文档，上传后自动切分入库</p>
      </div>
    </header>

    <!-- 上传区：虚线框 = 可点可选 -->
    <section class="upload-card">
      <div class="uc-icon" aria-hidden="true">📄</div>
      <div class="uc-body">
        <input ref="fileInput" type="file" accept=".md,.txt,.pdf" class="uc-input" />
        <p class="uc-hint">支持 .md / .txt / .pdf · 单个不超过 5MB · 同名覆盖前会确认</p>
      </div>
      <button class="uc-btn" :disabled="uploading" @click="upload">
        {{ uploading ? '上传中…' : '上传' }}
      </button>
    </section>

    <p v-if="error" class="msg error">😢 {{ error }}</p>
    <p v-if="message" class="msg success">{{ message }}</p>

    <section class="file-list">
      <div class="fl-head">
        <span>已入库文件</span>
        <span class="fl-count">{{ files.length }} 个</span>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="!files.length" class="empty">暂无文件，先上传一个吧</div>

      <div v-for="f in files" :key="f.filename" class="file-item">
        <span class="fi-icon" aria-hidden="true">📄</span>
        <span class="name" :title="f.filename">{{ f.filename }}</span>
        <button class="danger" :disabled="deleting === f.filename" @click="remove(f.filename)">
          {{ deleting === f.filename ? '删除中...' : '删除' }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* ===== 寓见 · 知识库管理（多主题版） =====
   比用户页更沉稳：装饰全免，靠字重、留白和层次撑场面。 */

.admin-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 16px 96px;   /* 底部留白给小船 */
  min-height: 100vh;
  background:
      radial-gradient(560px 280px at 90% -5%, color-mix(in srgb, var(--primary) 12%, transparent), transparent),
      var(--bg);
}

/* ===== 页头 ===== */
.page-head { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; }
.ph-icon {
  width: 52px; height: 52px; flex-shrink: 0;
  border-radius: calc(var(--radius-card) - 4px);
  background: var(--primary-tint);
  display: grid; place-items: center;
  font-size: 26px;
  box-shadow: var(--shadow-btn);
}
.page-head h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text);
  font-family: var(--font-display);
}
.page-head p { margin: 4px 0 0; font-size: 13px; color: var(--text-secondary); }

/* ===== 上传卡 ===== */
.upload-card {
  display: flex; align-items: center; gap: 16px;
  padding: 18px 20px;
  margin-bottom: 14px;
  background: var(--surface);
  border: 1.5px dashed color-mix(in srgb, var(--primary) 45%, var(--border));
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.upload-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-btn);
}
.uc-icon {
  width: 44px; height: 44px; flex-shrink: 0;
  border-radius: 12px;
  background: var(--primary-tint);
  display: grid; place-items: center;
  font-size: 22px;
}
.uc-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }

/* 原生 file input 的有限美化 */
.uc-input {
  width: 100%;
  font-size: 13px;
  color: var(--text-secondary);
}
.uc-input::file-selector-button {
  margin-right: 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 7px 14px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  cursor: pointer;
  transition: border-color .2s ease, color .2s ease;
}
.uc-input::file-selector-button:hover {
  border-color: var(--primary);
  color: var(--primary-deep);
}
.uc-hint { margin: 0; font-size: 12px; color: var(--text-tertiary); }

/* 上传按钮：主题渐变 */
.uc-btn {
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-pill);
  padding: 10px 22px;
  background: var(--grad-primary);
  color: var(--on-primary);
  font-size: 14px; font-weight: 700;
  font-family: var(--font-display);
  cursor: pointer;
  box-shadow: var(--shadow-btn);
  transition: transform .2s ease, opacity .2s ease;
}
.uc-btn:hover:not(:disabled) { transform: translateY(-2px); }
.uc-btn:active:not(:disabled) { transform: scale(.96); }
.uc-btn:disabled { opacity: .55; cursor: not-allowed; }

/* ===== 提示条 ===== */
.msg {
  margin: 0 0 14px;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
}
.msg.error {
  color: var(--error);
  background: var(--error-bg);
  border: 1px solid var(--error-border);
}
.msg.success {
  color: var(--success);
  background: var(--success-bg);
  border: 1px solid var(--success-border);
}

/* ===== 文件列表 ===== */
.file-list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}
.fl-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px;
  font-size: 14px; font-weight: 600;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--primary-tint) 45%, var(--surface));
}
.fl-count {
  font-size: 12px; font-weight: 500;
  color: var(--text-secondary);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 2px 10px;
}

.file-item {
  display: flex; align-items: center; gap: 12px;
  padding: 13px 18px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
  transition: background .15s ease;
}
.file-item:last-child { border-bottom: 0; }
.file-item:hover { background: var(--bg); }

.fi-icon {
  width: 34px; height: 34px; flex-shrink: 0;
  border-radius: 10px;
  background: var(--primary-tint);
  display: grid; place-items: center;
  font-size: 17px;
}
.name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 删除按钮：幽灵危险态 */
.danger {
  flex-shrink: 0;
  border: 1.5px solid var(--error-border);
  border-radius: var(--radius-pill);
  padding: 6px 16px;
  background: transparent;
  color: var(--error);
  font-size: 13px;
  cursor: pointer;
  transition: background .2s ease, transform .2s ease, opacity .2s ease;
}
.danger:hover:not(:disabled) { background: var(--error-bg); transform: translateY(-1px); }
.danger:active:not(:disabled) { transform: scale(.96); }
.danger:disabled { opacity: .55; cursor: not-allowed; }

/* 空状态 */
.empty { padding: 36px 20px; color: var(--text-tertiary); text-align: center; font-size: 14px; }
</style>
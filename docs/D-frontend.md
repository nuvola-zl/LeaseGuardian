# D 域交付说明：前端（Vue 3 + TypeScript）

## 1. D 域负责范围

D 域负责 LeaseGuardian 前端用户界面与前后端联调适配。

### 已覆盖能力

- 登录 / 注册页
- 登录态保存与路由守卫
- `/home` 双业务入口
- `/repair` 报修 / 工单会话入口
- `/lease` 租约 / 退租 / 结算会话入口
- 通用聊天壳：`scene` 透传、`session_id` 续接、SSE 流式渲染
- 左侧多会话列表：会话拉取、切换、新建
- 刷新恢复聊天历史
- persona 风格切换：原语气 / 温柔 / 毒舌 / 东北
- 401 统一跳登录、断网兜底、请求超时控制

### 明确不负责

- 登录 / 注册 / JWT：B 域
- 工单业务、Python 编排、会话底座：A 域
- 退租业务、结算规则、persona 生成、SSE 出口：C 域

---

## 2. 启动方式

```powershell
cd E:\pyidea\LeaseGuardian\frontend
npm install
npm run dev
```

默认端口：

```text
5173
```

开发代理：

```ts
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8080',
      changeOrigin: true,
      rewrite: p => p.replace(/^\/api/, ''),
    },
    '/py': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: p => p.replace(/^\/py/, ''),
    },
  },
}
```

说明：`/api` 是前端代理前缀，对应 Java 8080；`/py` 是前端代理前缀，对应 Python 8000。

---

## 3. 技术栈

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- axios：Java 接口
- fetch + ReadableStream：Python `/chat` SSE 流式接口

---

## 4. 页面与路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录页 | 无需 token；登录成功跳 `/home` 或回 redirect |
| `/register` | 注册页 | 注册成功提示后跳登录 |
| `/home` | 首页 | 双入口卡片，需登录 |
| `/repair` | 报修聊天页 | `scene=REPAIR` |
| `/lease` | 退租聊天页 | `scene=CHECKOUT` |
| `/chat` | 重定向 | 兼容旧路径，重定向到 `/home` |

未登录访问受保护路由时，由路由守卫统一跳 `/login`，并带回 `redirect`。

---

## 5. 依赖接口

### 5.1 B 域：账号接口

| 接口 | 用途 |
|---|---|
| `POST /api/auth/register` | 注册 |
| `POST /api/auth/login` | 登录，保存 token |
| `GET /api/auth/me` | 当前用户 + 租约摘要 |

### 5.2 A 域：会话与历史接口

| 接口 | 用途 |
|---|---|
| `GET /api/chat/sessions?scene=REPAIR` | 报修会话列表 |
| `GET /api/chat/sessions?scene=CHECKOUT` | 退租会话列表 |
| `GET /api/chat/sessions/{session_id}/messages` | 拉历史消息 |

### 5.3 C/A 共用：对话入口

```http
POST /py/chat
Authorization: Bearer <JWT>
Content-Type: application/json
```

请求体：

```json
{
  "message": "厨房水龙头漏水",
  "scene": "REPAIR",
  "session_id": "可选",
  "persona": "可选"
}
```

响应：`text/event-stream`

事件：

| event | 说明 |
|---|---|
| `status` | 阶段进度，收到什么显示什么 |
| `token` | 逐字输出，仅 persona 请求保证出现 |
| `done` | 最终结果，前端以 `done.answer` 为准，并取 `done.session_id` |
| `error` | 流内错误，HTTP 仍为 200 |

---

## 6. 关键设计

### 6.1 Java 两层拆包

Java 接口返回统一壳：

```json
{ "code": "A00000", "msg": "success", "data": {}, "request_id": null }
```

前端必须拆两层：

```ts
res.data        // Result 壳
res.data.data   // 真正业务数据
```

统一使用 `unwrapResult<T>()`，禁止 Java / Python 解析混用。

### 6.2 scene 语义

`scene` 只是默认上下文，不是硬路由。

- `/repair` 传 `REPAIR`
- `/lease` 传 `CHECKOUT`
- 用户消息内容与 scene 冲突时，以后端内容优先结果为准
- 前端不做“报修 / 退租”关键词业务判断

### 6.3 session_id

- 首次请求不传 `session_id`
- `done.session_id` 是唯一可靠来源
- 后续同一会话请求必须带回
- `/repair` 和 `/lease` 会话隔离
- 退出登录清理本地会话状态

### 6.4 刷新恢复

当前入口存在本地 `session_id` 时：

1. 拉会话列表
2. 命中本地 session 则选中
3. 拉历史消息渲染
4. 未命中则回退到最新会话或新建会话

历史接口失败时，可临时降级使用本地快照。

### 6.5 SSE 顺滑渲染

- token 不逐条直接 setState，先进入 `pendingText`
- 40ms 批量 flush 到气泡
- `done.answer` 到达后整体替换气泡，避免半句定格
- 离开页面或重复发送时 `AbortController` 取消旧流

### 6.6 persona

localStorage key：

```text
lg_persona
```

默认不存值，表示不传 persona；选择 SWEET / SASSY / NORTHEAST 后发送时带上。

---

## 7. 本地存储键位

| key | 用途 |
|---|---|
| `lg_token` | JWT |
| `lg_persona` | 风格人设 |
| `lg_chat_session_REPAIR` | 报修入口当前会话快照 |
| `lg_chat_session_CHECKOUT` | 退租入口当前会话快照 |

退出登录会清理 `lg_token` 与 `lg_chat_session_*`。

---

## 8. 已完成

- 登录 / 注册 / 登录态保持
- 路由守卫与 redirect 回跳
- 双入口首页
- 双 scene 聊天页
- SSE 流式输出与进度文案
- persona 风格切换
- session_id 续接
- 历史接口恢复聊天
- 左侧多会话列表
- 401 / A00010 跳登录
- A00011 无权访问兜底

---

## 9. 未做 / 后置

- 正式工单结构化列表页
- 退租进度卡片
- 移动端完整适配
- 生产环境 nginx / HTTPS / SSE buffering 配置
- token 安全策略升级（当前 localStorage，课设可接受，生产建议 httpOnly cookie）

---

## 10. TODO

- 补充前端 README 截图
- 补充 `.env.example`
- 美化 UI 后回归 `npm run type-check`
- 生产部署补充 nginx SSE 反代说明
- 清理测试账号与脏会话数据

---

## 11. 边界声明

D 域后续只维护：

- 页面与路由
- 前端状态管理
- 接口请求适配
- SSE / 会话 / persona 前端交互
- UI 样式与可用性

不主动修改：

- B 域账号/JWT
- A 域工单/会话底座/Python 编排
- C 域退租业务与风格生成规则

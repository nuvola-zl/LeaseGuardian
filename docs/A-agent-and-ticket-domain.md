# A 域交付说明：报修工单域 + Python 编排层

## 1. A 域负责范围

A 域负责 LeaseGuardian 的“租客报修”主链路，以及 Python 编排层公共底座。

### 已覆盖能力

- 登录态识别：通过 JWT + `/auth/me` 获取当前用户
- 自然语言报修：自动创建报修工单
- 查询工单：查询当前用户名下工单
- 维修责任咨询：基于 `rag/docs/repair_policy.md`
- 维修价格咨询：基于 `rag/docs/price_table.md`
- repair RAG：与 checkout RAG 共用同一套检索核心
- 会话管理：session 创建、消息落库、历史恢复接口
- 短期记忆 v1：最近历史注入回答 prompt、最小 `state_json`

### 明确不负责

- 登录 / 注册 / JWT 签发：B 域
- 退租 / 押金 / 结算 / 损坏赔偿：C 域
- 前端页面：D 域

---

## 2. 启动方式

### 2.1 Java 业务层

```powershell
cd E:\pyidea\LeaseGuardian\java-service
mvn spring-boot:run
```

默认端口：

```text
8080
```

### 2.2 Python 编排层

```powershell
cd E:\pyidea\LeaseGuardian\agent-service
.\.venv\Scripts\Activate.ps1
uvicorn agent_service.main:app --host 127.0.0.1 --port 8000
```

默认端口：

```text
8000
```

---

## 3. A 域核心接口

## 3.1 对话入口

```http
POST /chat
Authorization: Bearer <JWT>
Content-Type: application/json
```

请求体：

```json
{
  "message": "厨房水龙头漏水",
  "scene": "REPAIR",
  "session_id": "可选"
}
```

响应：

```json
{
  "answer": "已创建报修工单：id=20，status=REGISTERED，tenant_id=1",
  "session_id": "1"
}
```

说明：

- 不带 `session_id` 时，首条消息自动创建会话
- 后续请求建议携带同一个 `session_id`
- `scene` 是默认上下文，不做硬隔离
- 当前响应已升级为 SSE 流式输出，旧 JSON 调试方式需改为读取 SSE 事件

---

## 3.2 工单接口（Java）

### 创建工单

```http
POST /tickets
```

请求体：

```json
{
  "tenant_id": 1,
  "description": "厨房水龙头漏水",
  "request_id": "req-001"
}
```

说明：

- `tenant_id` 必须等于 `user.id`
- `request_id` 可空；非空时用于幂等防重

### 查询工单列表

```http
GET /tickets
GET /tickets?tenant_id=1
```

### 查询工单详情

```http
GET /tickets/{id}
```

### 更新工单状态

```http
PATCH /tickets/{id}/status
```

请求体：

```json
{
  "status": "PROCESSING"
}
```

当前状态机：

```text
REGISTERED -> PROCESSING
PROCESSING -> DONE
REGISTERED -> CANCELLED
PROCESSING -> CANCELLED
```

---

## 3.3 会话与历史接口

### 创建会话（服务间）

```http
POST /chat/sessions?userId=1
```

### 写消息（服务间）

```http
POST /chat/sessions/{session_id}/messages
```

### 更新会话状态（服务间）

```http
PATCH /chat/sessions/{session_id}/state
```

### 前端拉会话列表

```http
GET /api/chat/sessions?scene=REPAIR
Authorization: Bearer <JWT>
```

或：

```http
GET /api/chat/sessions?scene=CHECKOUT
Authorization: Bearer <JWT>
```

返回字段：

```json
{
  "session_id": 1,
  "title": "厨房水龙头漏水",
  "created_at": "2026-10-26T16:00:00.000",
  "updated_at": "2026-10-26T16:02:00.000"
}
```

### 前端拉历史消息

```http
GET /api/chat/sessions/{session_id}/messages
Authorization: Bearer <JWT>
```

返回字段：

```json
{
  "role": "USER",
  "content": "厨房水龙头漏水",
  "created_at": "2026-10-26T16:00:00.000"
}
```

---

## 4. 数据表说明

### A 域主表

```text
repair_ticket
```

核心字段：

- `id`
- `tenant_id` -> `user.id`
- `description`
- `status`
- `related_lease_id`（预留）
- `request_id`（幂等）
- `created_at`
- `updated_at`

### 会话公共底座

```text
chat_session
chat_message
```

说明：

- 会话层是公共底座，不专属于 A
- A 当前只写最小状态：
  - `common.last_route`
  - `repair.last_ticket_id`
- C 后续如需写状态，只允许写 `checkout` 命名空间
- 业务真相仍以业务表为准，`state_json` 只是会话级临时状态

---

## 5. RAG 说明

repair RAG 与 checkout RAG 共用同一套核心。

### 语料文件

```text
rag/docs/repair_policy.md
rag/docs/price_table.md
rag/docs/checkout.md
```

### 构建与评测

```powershell
cd E:\pyidea\LeaseGuardian\agent-service
.\.venv\Scripts\python.exe -m agent_service.rag.ingest repair
.\.venv\Scripts\python.exe -m agent_service.rag.eval_repair
```

### 当前能力

- 维修责任问答
- 维修参考价问答
- checkout 条款问答由 C 域复用同一套检索底座

---

## 6. 记忆与会话边界

### 当前已完成

- 会话创建
- 消息落库
- 历史查询
- 最近历史注入回答 prompt
- 最小 `state_json`

### 当前未做

- summary 压缩
- 复杂流程跨刷新无缝续跑
- 长期记忆
- 跨入口共享上下文

### 原则

- 历史只进回答 prompt，不进路由
- `understand_node` 只看当前消息
- 退租/报修业务状态以业务表为准，不靠聊天记录猜

---

## 7. A 域验收清单

后续环境方便时可按此验收：

- [ ] 登录后可进入报修入口
- [ ] 输入“厨房水龙头漏水”可创建工单
- [ ] 输入“查工单”只查询，不建单
- [ ] 输入“水龙头维修多少钱”只回答价格，不建单
- [ ] 输入“自然老化谁负责”只回答责任，不建单
- [ ] 同一 session 可持续写入消息
- [ ] 刷新后可通过历史接口恢复聊天记录
- [ ] 会话列表接口只返回当前用户自己的会话
- [ ] `state_json.repair.last_ticket_id` 在报修后正确写入

---

## 8. 已知 TODO

- 目录统一：语料、RAG、脚本位置需收敛
- smoke 脚本移到 `scripts/`，避免触发服务热重载
- `requirements.txt` 最终补全
- `.env.example` 最终补全
- 正式演示前清理测试脏数据

---

## 9. A 域边界声明

A 域后续只维护：

- `/tickets` 工单接口
- repair RAG
- Python 编排公共底座中的会话/记忆基础能力
- 报修分支话术与流程

不主动修改：

- B 域登录/JWT
- C 域退租业务
- D 域前端实现



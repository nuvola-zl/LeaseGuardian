# C 域交付说明：退租结算域 + 风格层 + SSE 流式

## 1. C 域负责范围

C 域负责 LeaseGuardian 的"租客退租"主链路，以及对话出口的统一风格层与流式输出。

### 已覆盖能力

- 退租全流程：发起 → 搬离日 → 损坏登记 → 结算核算 → 确认/取消
- 资金确认闸口：结算单版本化 + 乐观锁，确认是唯一扣款入口
- 条款铁律：每个非零扣款项强制挂条款依据（bill_item basis 三件套），无依据不出单
- 整月制公式：`剩余整月数 = max(0, 到期年月 − 搬离年月 − 1)`，搬离当月与到期当月不计
- 到期旁路：lease 读取统一出口惰性判 EXPIRED
- checkout RAG：条款级切分 + BM25/向量双路召回 + RRF 融合，评测集 15/15
- 风格层（persona）：SWEET / SASSY / NORTHEAST，润色走独立模型（qwen-flash）
- SSE 流式输出：status 进度事件 + token 逐字推送 + done 兜底
- 端到端冒烟脚本：ALL 9 CHECKS

### 明确不负责

- 登录 / 注册 / JWT：B 域
- 报修工单：A 域
- 会话底座（chat_session/chat_message、记忆注入）：A 域公共层
- 前端页面：D 域

---

## 2. 启动方式

依赖：Java（8080）先于 Python（8000）启动；SQL 已执行；RAG 已入库。

```powershell
# RAG 入库（首次或条款变更后）
cd E:\pyidea\LeaseGuardian\agent-service
.\.venv\Scripts\python.exe -m agent_service.rag.checkout_ingest

# Python 编排层
.\.venv\Scripts\python.exe -m uvicorn agent_service.main:app --host 127.0.0.1 --port 8000
```

## 3. 核心接口契约

### 3.1 对话入口（含 style 与流式）

```http
POST /chat          # Python :8000
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "message": "我要退租",
  "scene": "CHECKOUT",
  "session_id": "可选",
  "persona": "SASSY"
}
```

响应为 `text/event-stream`，四种事件：

| event  | data                                                                              | 说明                  |
| ------ | --------------------------------------------------------------------------------- | ------------------- |
| status | `{"step": "understanding\|verifying\|querying\|creating\|processing\|polishing"}` | 阶段进度，子集出现，顺序不固定     |
| token  | `{"text": "..."}`                                                                 | 润色词元，仅带 persona 时出现 |
| done   | `{"session_id": "1", "answer": "完整文本"}`                                           | 以 done.answer 为准    |
| error  | `{"message": "..."}`                                                              | 流内错误恒为 HTTP 200     |

旧请求不传 persona：只有 status + done，无 token，属正常。

### 3.2 退租接口（Java :8080，服务间调用，不带 JWT）

| 接口                                           | 说明                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------- |
| `GET /checkout/cases/current?tenantId=`      | 当前活跃退租单（APPLYING/AWAITING_CONFIRM），无则 null                          |
| `POST /checkout/cases`                       | 创建退租单；body `request_id` 可空（空则服务端 UUID），`move_out_date` 可选           |
| `POST /checkout/cases/{id}/move-out-date`    | 登记/修改搬离日                                                            |
| `POST /checkout/cases/{id}/damages`          | 登记损坏；TENANT 自动核定（final=参考价），MANUAL_PENDING 置待人工                     |
| `POST /checkout/cases/{id}/settlement`       | 生成/重算结算（旧草稿自动作废，版本 +1）                                              |
| `GET /checkout/cases/{id}/settlement-detail` | 结算明细：bill + bill_items + damage_items                               |
| `POST /checkout/cases/{id}/confirm`          | 确认（body 带 `settlement_version`）；同事务完成 lease TERMINATED + 关账单 + 释放房号 |
| `POST /checkout/cases/{id}/cancel`           | 取消（APPLYING/AWAITING_CONFIRM 可取消），lease 回 ACTIVE                    |

约定：

- `tenantId` 一律由 Python 从登录态取 `user_context.user_id`，禁止从消息文本抠；
- 全局 SNAKE_CASE；错误统一 HTTP 语义 + Result body（成功码仅 `A00000`）；
- 关键错误码：`A02002` 租约不存在、`A02004` 状态非法、`A02010` 搬离日非法、`A02011` 版本冲突、`A02012` 待人工阻塞、`A02013` 条款缺失。

### 3.3 状态机

```text
lease:  ACTIVE → TERMINATING → TERMINATED（旁路：到期读时惰性转 EXPIRED）
case:   APPLYING → AWAITING_CONFIRM → COMPLETED
                    ↘ CANCELLED（确认前免费取消）
约束：一人同时最多一张活跃 case（uk_checkout_active_case）
```

## 4. 数据表（C 域）

`checkout_case` / `damage_item` / `bill` / `bill_item`：见 `sql/V3__checkout_tables.sql`。
要点：`checkout_case.active_case_flag` 为生成列唯一索引；`bill_item` 非零行强制 `basis_*` 三件套；初始化脚本生成近 3 个月 `UTILITY_DEBT/OPEN` 账单。

## 5. RAG（checkout 域）

- 语料：`rag/docs/checkout.md`（示例条款，正式需替换合同原文）
- 切分：按 `##` 条款级
- 向量：Chroma 本地持久化（`rag/chroma_db/`，已 gitignore）；embedding `text-embedding-v3`（阿里，1024 维）
- 检索：BM25（按字）+ 向量双路，RRF(k=60) 融合，rerank 接口预留未启用
- 评测：`python -m agent_service.rag.eval_checkout`，15 条，当前 15/15
- 条款引用格式：`（依据 checkout_policy CLAUSE-XXX）`

## 6. 已完成 / 未做

已完成：全部退租链路、资金闸口、条款铁律、整月公式、EXPIRED 惰性旁路、RAG 双路、风格层、SSE、冒烟 ALL 9。
未做（明确后置）：真实支付对接、续租、违约金、房东端、长期记忆、摘要压缩、rerank 实装、历史存原文优化。

## 7. C 域验收清单

- [ ] 新用户：我要退租 → 搬离日 → 报损坏 → 结算数字按公式核对 → 确认 → 房间可再注册
- [ ] 确认前取消：免费，lease 回 ACTIVE
- [ ] 重复确认/乱序指令：明确拒绝，不产生二次副作用
- [ ] 报修语句不串入 checkout（防串域回归）
- [ ] 退租话术带条款引用；数字、id、状态词与单据一致
- [ ] persona=SASSY 时语气变化且事实字段一字不改；不传 persona 与旧版一致
- [ ] 刷新页面流程不丢（业务表对齐）

## 8. 已知 TODO

- `checkout.md` 示例条款替换为真实合同原文（替换后重跑 ingest + 评测）
- 历史存原文（raw_answer）优化：当前落库为润色后版本
- smoke 脚本移 `scripts/` 目录
- rerank 实装（bge-reranker，接口已预留）

## 9. C 域边界声明

只维护：`/checkout/*` 接口、checkout RAG、风格层（persona_node / polish_answer）、SSE 出口、smoke 脚本。
不主动修改：A 域编排底座与会话层、B 域鉴权、D 域前端。



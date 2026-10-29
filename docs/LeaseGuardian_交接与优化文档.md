# LeaseGuardian（寓见）项目交接与优化文档

> 版本：v1.0　生成日期：2026-10-29
> 用途：新 AI 接手材料 / 项目 owner 自查 / 简历素材底稿

---

## 一、项目背景

**LeaseGuardian（寓见）智能租赁管家**：租客的对话式租务入口，一个聊天窗口办所有租住事务（报修、退租、条款咨询）。

**技术栈**：MySQL 8 + Spring Boot 3（Java 17，业务与状态机） + Python FastAPI + LangGraph（AI 编排） + Chroma（向量库） + 阿里百炼（qwen-plus / qwen-flash / text-embedding-v3 / gte-rerank-v2）。

**团队分工**：

| 角色 | 负责 |
|---|---|
| 项目 owner（协调与拍板） | 需求裁决、验收、所有关键设计决策的最终签字人 |
| A | 报修工单域、Python 编排公共底座（会话/记忆/检索核心） |
| B | 账号租约域（注册/登录/JWT/统一返回结构） |
| C | 退租结算域、风格层、SSE 流式、RAG 检索管线 |
| D | 前端（登录/首页双入口/聊天页/会话列表/管理界面） |

**核心设计哲学（不可动摇）**：

1. **LLM 无执行权**：模型只产出意图与措辞；状态迁移、资金、幂等、并发全部由 Java 裁决。
2. **对话无状态，状态全在单据**：每轮对话先查库对齐业务状态，换设备/刷新不丢流程。
3. **确认是资金唯一闸口**：结算单版本化 + 乐观锁；确认前可免费取消。
4. **扣款必须挂条款**：每个非零 bill_item 强制 basis 三件套，无依据不出单。

**封板业务规则**：月租 800、押金 1600（押二付一）、租期固定 6 个月；退租结算公式：应退 = 押金 + 剩余整月租金 − 水电欠费 − 损坏赔偿；整月数 = max(0, 到期年月 − 搬离年月 − 1)（搬离当月与到期当月不计）；损坏分人为赔/自然老化不赔/待人工三类，待人工阻塞确认。

---

## 二、系统架构

```
用户消息
  → 前端（/repair、/checkout 双入口，scene 标识）
  → POST /chat（FastAPI, SSE 流式）
  → understand_node（第一层 LLM 意图抽取 → 第二层正则/规则兜底 → 第三层闲聊）
  → 分流：
      报修  → identity → 建单/查单/维修咨询
      退租  → identity → context（对齐单据状态）→ router（状态机分流）→ 业务节点
      咨询  → checkout_consult / repair_consult（检索 + 拒答）
      闲聊  → chat_node
  → answer_node（事实拼装）→ persona_node（flash 人设润色，SSE 逐字推）
  → Java /checkout/*（唯一执行入口，状态机 + 同事务联动）
  → MySQL（业务表 + 会话表）
```

**RAG 检索管线**（checkout / repair 共用 core）：

```
查询改写（qwen-flash）
  → BM25（按字切）+ 向量双路召回（checkout/repair 域 + custom 公共域）
  → RRF(k=60) 融合
  → gte-rerank-v2 精排（rerank_score 写回候选）
  → 拒答阈值 0.3（分数不足 → "没查到明确规定"兜底话术）
```

**记忆体系**：

- 短期：最近 8 条原文注入回答 prompt（不进路由）。
- 摘要：会话超 12 条消息滚动压缩（flash 生成，存 state_json.common.summary）。
- 状态：state_json 按命名空间隔离（common / repair / checkout）。

---

## 三、开发过程回顾（真实时间线）

| 阶段 | 内容 | 关键产出 |
|---|---|---|
| 1. 底座 | 四表 DDL、初始化账单、Java 状态机 | SQL V3、/checkout 全套接口 |
| 2. 编排 | Python 图、三层路由、防串域守卫 | graph.py、smoke_checkout.py |
| 3. RAG | 条款入库、双路召回 + RRF、评测集 15 条 | rag/、eval_checkout.py |
| 4. 契约修复 | requestId 放宽、snake_case 对齐、scene 兜底 | 全链路契约统一 |
| 5. 体验 | persona 三风格、SSE 流式、进度事件 | persona_node、StreamingResponse |
| 6. 记忆 | 摘要压缩、会话隔离、state_json | summarize_history |
| 7. 泛化 | 文件上传（md/txt/pdf）、管理界面接口 | /rag/upload、/admin |
| 8. 健壮 | 模糊日期推断、查询改写、拒答层、公共域 | _infer_fuzzy_date、rewrite_query、rerank 阈值 |

**开发方式说明**：本项目由项目 owner 协调多个 AI 成员协作完成，采用"消息内补丁 + 文件对账"的迭代方式。这导致代码存在合理的演进痕迹（见第五节"补丁漂移史"）。

---

## 四、代码现状

### 4.1 模块清单

| 文件 | 职责 | 状态 |
|---|---|---|
| `sql/V3__checkout_tables.sql` | 四表 DDL + 唯一约束 + 初始化账单 | 稳定 |
| Java `CheckoutServiceImpl` | 状态机、结算引擎、确认闸口、EXPIRED 惰性迁移 | 稳定 |
| `tools/checkout_tools.py` | checkout 服务间调用（snake_case） | 稳定 |
| `graph.py` | 全部节点与路由（约 800 行） | 功能完整，**待重构** |
| `llm.py` | extract/改写/润色/摘要（plus 与 flash 分工） | 稳定 |
| `rag/core.py` | 检索公共核心（多域 BM25/向量/RRF/rerank/入库） | 稳定 |
| `main.py` | /chat SSE、session 管理、/rag/upload、/admin | 稳定 |
| `smoke_checkout.py` | 端到端冒烟，9 项断言 | 稳定（验收基准） |
| `rag/eval_checkout.py` | RAG 评测集 15 条 | 稳定（验收基准） |

### 4.2 已知补丁史（重构时的"债单"）

以下为开发中真实踩坑并修复的记录，每条都是一条设计教训：

1. **requestId 必填事故**：checkout 创建曾要求 requestId，与全局"可空 + 服务端 UUID"契约冲突 → 已放宽。
2. **snake_case 契约**：Python 早期传 camelCase，全局 SNAKE_CASE 下全字段映射失败（requestId 被兜底掩盖、moveOutDate 暴露）→ 已统一。
3. **路由串域**："厨房水龙头漏水"被 checkout 抽取抢走 → understand 加守卫，报修优先。
4. **scene 传递漏洞**：前端只在新会话带 scene，后续消息丢失 → 后端从会话表兜底。
5. **excerpt 空行坑**：`splitlines()[1]` 取到空行 → 改"跳空行取正文"（checkout 修过、repair 曾漏同步——**同构坏味道的实证**）。
6. **upsert 语义误解**：upsert 只就 id 论 id，删条款留"幽灵块" → 管理端改"先删后插"（D 侧执行中）。
7. **域隔离盲区**：上传文件进 custom 域，仅 checkout 可见 → custom 改公共域，双入口可查。
8. **拒答缺失**：检索"有就答"导致错条款硬答 → 加 rerank_score ≥ 0.3 阈值。
9. **意图集合过窄**：checkout schema 只覆盖退租流程，通用咨询进不来 → is_policy_consult 兜底（应进 schema 泛化，见优化清单）。

### 4.3 模型分工

| 模型 | 用途 |
|---|---|
| qwen-plus | 意图抽取、闲聊（要聪明的地方） |
| qwen-flash | 查询改写、人设润色、摘要（要快的地方） |
| text-embedding-v3 | 条款向量化（1024 维） |
| gte-rerank-v2 | 检索精排（relevance_score 兼做拒答依据） |

---

## 五、可优化点清单

### P0 结构债（本次优化主线）

| # | 优化点 | 现状病灶 | 目标形态 | 验收 |
|---|---|---|---|---|
| 1 | 合并同构咨询节点 | checkout_consult / repair_consult 90% 重复，已两次不同步出 bug | 单一 `consult_node(domain)` 参数化节点 | 两域咨询行为一致；excerpt 逻辑只有一份 |
| 2 | 意图 schema 泛化 | 六类意图全是退租流程，通用知识靠 graph 层补丁 | 意图集合加 `policy_consult` 一等公民；extract 层直接支持 | "楼道能不能堆杂物"类问题一次进咨询，不经补丁层 |
| 3 | 简化三层兜底 | understand 三层逻辑交织，调试要推理全链 | LLM 主路由 + 两道硬护栏（资金词表、LLM 故障降级） | 冒烟 9 项 + 新增意图边界用例 |
| 4 | 拒答层降级兜底 | gte 不可用时退回"有就答" | 降级用向量距离（1-dist）阈值兜底 | 模拟 gte 故障，拒答仍生效 |

### P1 工程质量债

- **历史存原文**：落库加 `raw_answer`（润色前文本），展示/审计用原文，风格切换可重放。
- **魔法数字收编**：0.3 / 12 / 8 / top_k=2 / 0.02 等集中到 config 或常量区。
- **纯函数单测**：整月公式、模糊日期推断、RRF 融合、状态机转移表（pytest，无外部依赖）。
- **graph.py 拆模块**：按域拆 `nodes/checkout.py`、`nodes/repair.py`、`routing.py`，graph.py 只留 build。
- **`_load_active_case` 加缓存**：每轮 understand 都调 /auth/me + /checkout/current，加 5~10 秒 TTL。
- **`retrieve_first_clause` 的 min_rrf_score=0.02 修正**：RRF 分数无相关度语义（动态范围 0.014~0.016），应改判 rerank_score 或向量距离。

### P2 体验增强（可选）

- chat_node 闲聊接 SSE 流式（现在只有润色层流式）。
- 摘要压缩异步化（当前同步，越阈值时回答延迟 +1~2 秒）。
- `state_json.checkout` 启用：存"等待中槽位"等会话级临时状态。
- 管理界面正式版（D 负责：整文件替换语义、hash 去重、管理员权限）。

---

## 六、验收红线（优化期间任何时刻都必须保持）

```text
□ python -m agent_service.smoke_checkout      → ALL 9 CHECKS PASSED
□ python -m agent_service.rag.eval_checkout   → 15/15
□ /chat 四条路径冒烟：
    报修建单 / 退租主线（发起→日期→损坏→确认）/
    确认前取消 / 防串域（"厨房水龙头漏水"只建单不进退租）
□ 风格层：SASSY 时事实字段（数字/id/状态/条款号）一字不改
□ SSE 事件流：status → token（带 persona 时）→ done，done.answer 为最终文本
```

---

## 七、给接手 AI 的第一周任务建议

**Day 1｜只读，不改码**
1. 跑通两条验收红线（smoke + eval），确认环境健康。
2. 按 §四.2 补丁史逐条在代码里找到对应实现，理解"为什么存在"。
3. 画出你理解的路由决策表（消息 → 节点），与项目 owner 对一遍。

**Day 2~3｜P0-1 + P0-2（同构合并 + 意图泛化）**
- 合并 consult 节点；意图集合加 policy_consult 并收编 is_policy_consult 补丁。
- 每步合并后立刻跑冒烟，红线掉了立刻回滚定位。

**Day 4~5｜P0-3 + P1 债务**
- 三层兜底简化；魔法数字收编；补纯函数单测（公式、日期推断、RRF）。

**第二周｜P0-4 拒答降级 + P1 收尾**
- 向量距离兜底；graph.py 拆模块；历史存原文。

**全程纪律**
- 每个改动一个 commit，message 用 `refactor(scope): ...` 规范；
- 任何"行为变化"必须与项目 owner 确认；"形态变化"（重构）不得改变行为；
- 拿不准的设计，先问再写——本项目所有关键决策都有 owner 签字记录。

---

*本文档由 C 与项目 owner 共同整理，补丁史与优化清单均为真实开发记录。*

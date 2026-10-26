# LeaseGuardian 总交付文档

> 本文档汇总 A/B/C/D 四域交付说明，作为项目总 README / 交付文档底稿。  
> 详细域文档见 `docs/` 下对应 md。

---

## 1. 项目一句话

LeaseGuardian（智能租赁管家）：租客注册即入住，登录后可进入两个业务入口办理：

- **报修 / 工单**
- **租约 / 退租 / 结算**

前端通过多入口对话式界面调用后端编排服务，后端按 `scene` 给出默认上下文，按消息内容优先完成建单、查单、条款咨询、退租、结算等业务。

---

## 2. 技术架构

```text
Browser
  └─ Vue3 Frontend (5173)
       ├─ /api/*  -> Java Spring Boot (8080)
       │             ├─ B 域：登录 / 注册 / JWT / 用户 / 租约
       │             ├─ A 域：工单 / 会话底座 / Python 编排支持
       │             └─ C 域：退租 / 结算 / 账单业务接口
       │
       └─ /py/*   -> Python FastAPI (8000)
                     └─ A/C 编排层：对话入口 /chat + SSE + persona + RAG
```

### 服务职责

| 域   | 负责内容                                          |
| --- | --------------------------------------------- |
| B 域 | 账号、注册即开通租约、JWT 鉴权、`/auth/me`                  |
| A 域 | 报修工单、工单接口、Python 编排底座、会话/记忆、repair RAG        |
| C 域 | 退租全流程、结算、资金闸口、checkout RAG、persona 风格层、SSE 出口 |
| D 域 | Vue3 前端、双入口、聊天 UI、SSE 接收、会话列表、历史恢复            |

---

## 3. 启动顺序

### 3.1 启动 Java（8080）

```powershell
cd E:\pyidea\LeaseGuardian\java-service
mvn spring-boot:run
```

### 3.2 启动 Python（8000）

方式一：终端启动

powershell
cd E:\pyidea\LeaseGuardian\agent-service
.\.venv\Scripts\Activate.ps1
uvicorn agent_service.main:app --host 127.0.0.1 --port 8000

方式二：PyCharm 运行配置（点绿色三角启动）

1. 打开 Run → Edit Configurations... → 左上角 + → 选 Python

2. 按以下内容填写：
   
   | 字段        | 值                                                              |
   | --------- | -------------------------------------------------------------- |
   | 名称        | agent-service                                                  |
   | 解释器       | E:\pyidea\LeaseGuardian\agent-service\.venv\Scripts\python.exe |
   | module    | uvicorn                                                        |
   | 参数        | agent_service.main:app --host 127.0.0.1 --port 8000            |
   | 工作目录      | E:\pyidea\LeaseGuardian\agent-service                          |
   | .env 文件路径 | E:\pyidea\LeaseGuardian\agent-service\.env                     |

3. 保存后点绿色三角 ▶ 启动，等价于方式一的命令

4. 可选：参数末尾加 --reload 实现代码热重载；调试（断点）时不要加

如需初始化 RAG，按 A/C 文档执行 ingest / eval。

### 3.3 启动前端（5173）

```powershell
cd E:\pyidea\LeaseGuardian\frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

---

## 4. 前端使用入口

| 页面  | 路径          | 说明               |
| --- | ----------- | ---------------- |
| 登录  | `/login`    | 已登录会跳 `/home`    |
| 注册  | `/register` | 注册成功提示后跳登录       |
| 首页  | `/home`     | 双业务入口            |
| 报修  | `/repair`   | `scene=REPAIR`   |
| 退租  | `/lease`    | `scene=CHECKOUT` |

未登录访问受保护页面会统一跳登录页，并在登录成功后回跳原目标。

---

## 5. 对外契约总则

### 5.1 Java 统一返回壳

所有 Java 接口返回：

```json
{ "code": "A00000", "msg": "success", "data": {}, "request_id": null }
```

规则：

- 唯一成功标准：`code === "A00000"`
- 不是 HTTP 200
- `request_id` 仅异常路径填充，成功恒为 null
- 多词字段统一 snake_case：`room_no`、`monthly_rent`、`user_id`

### 5.2 Python /chat SSE

`/chat` 返回 `text/event-stream`：

| event    | 说明                        |
| -------- | ------------------------- |
| `status` | 阶段进度，子集出现，顺序不固定           |
| `token`  | 逐字输出，仅 persona 请求保证出现     |
| `done`   | 最终答案与 `session_id`，前端以此为准 |
| `error`  | 流内错误，HTTP 仍为 200          |

### 5.3 scene 语义

`scene` 是默认上下文，不是权限闸门：

- `REPAIR`：报修默认上下文
- `CHECKOUT`：退租默认上下文
- 消息内容与 scene 冲突时，内容优先

### 5.4 session_id 语义

- 首次请求可不带 `session_id`
- `done.session_id` 是唯一可靠来源
- 后续同一会话必须带回
- 不同入口、不同用户会话隔离

---

## 6. 分域文档索引

| 域   | 文档                                  |
| --- | ----------------------------------- |
| A 域 | `docs/A-agent-and-ticket-domain.md` |
| B 域 | `docs/B-auth-domain.md`             |
| C 域 | `docs/C-checkout-domain.md`         |
| D 域 | `docs/D-frontend.md`                |

---

## 7. 核心能力总览

### 已完成

- 注册即入住，自动开通租约
- JWT 登录鉴权，`/auth/me` 用户与租约摘要
- 报修建单、查工单、维修责任/价格咨询
- 退租发起、搬离日、损坏登记、结算确认
- 结算版本化 + 乐观锁资金闸口
- repair / checkout RAG
- SSE 流式输出
- persona 风格层
- 会话创建、消息落库、历史恢复、会话列表
- 前端双入口聊天、刷新恢复、多会话切换

### 明确未做

- 真实支付对接
- 房东端 / 运营端
- 登录限流 / 验证码 / 强制下线
- 长期记忆 / summary 压缩
- rerank 实装
- 移动端完整适配
- 生产级部署与安全加固

---

## 8. 统一验收清单

- [ ] 新用户注册成功并自动开通租约
- [ ] 登录成功进入 `/home`
- [ ] `/repair` 发“厨房水龙头漏水”能建工单
- [ ] `/repair` 发“查工单”只查询不建单
- [ ] `/repair` 发“水龙头维修多少钱”只答价格不建单
- [ ] `/lease` 新用户发“我要退租”可进入退租流程
- [ ] 退租流程：搬离日 → 损坏登记 → 结算 → 确认/取消
- [ ] persona 风格输出存在且事实字段不跑偏
- [ ] SSE 有 status 进度，done 最终兜底
- [ ] 刷新页面历史恢复
- [ ] 会话列表按入口隔离
- [ ] 未登录访问受保护页面跳登录
- [ ] token 失效后统一回登录页
- [ ] 无生效租约账号访问退租有明确文案

---

## 9. 已知 TODO

### A 域

- 目录统一：语料、RAG、脚本位置收敛
- smoke 脚本移到 `scripts/`
- `requirements.txt` 补全
- `.env.example` 补全
- 清理测试脏数据

### B 域

- requestId 是否填充成功响应待 C 裁决
- 时间格式是否统一待 C 裁决

### C 域

- `checkout.md` 示例条款替换为真实合同原文
- 历史存原文优化
- rerank 实装
- smoke 脚本移 `scripts/`

### D 域

- 正式工单列表页
- 退租进度卡片
- 生产 nginx SSE 反代说明
- `.env.example`
- UI 美化回归

---

## 10. 边界与协作规则

- 各域只改自己边界，跨域改动先周知
- Java 契约变更必须同步 B/A/C/D
- Python `/chat` 事件契约变更必须同步 D
- 前端不猜业务字段，接口字段以域文档为准
- 发现文档与真实返回不一致，先停联调，回各自域修正

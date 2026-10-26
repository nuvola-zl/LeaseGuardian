# B 域交付说明：账号域（登录 / 注册 / JWT / 用户与租约）

## 1. B 域负责范围

B 域负责 LeaseGuardian 的账号体系与租约基础数据，以及跨域复用的 JWT 鉴权能力。

### 已覆盖能力
- 注册：开户 + 自动开通初始租约（单事务，六步：格式→重名→撞房→插 user→插 lease→返回）
- 登录：BCrypt 校验密码，通过签发 JWT
- 登录态校验：JWT 拦截器 + ThreadLocal 上下文（`BaseContext`）
- 当前用户查询：`GET /auth/me`（用户基本信息 + 租约摘要），**A 域 Python 的登录态识别依赖此接口**
- 按 id 查询用户（白名单 VO 出站，不含 password_hash）
- 公共鉴权底座：`/api/chat/**` 前端聊天接口的统一 JWT 校验由 B 域拦截器提供

### 明确不负责
- 工单 / 报修 / Python 编排 / 会话底座：A 域
- 退租 / 押金 / 结算 / 损坏赔偿 / checkout RAG：C 域
- 前端页面：D 域

---

## 2. 启动方式

B 域无独立启动项，随 Java 业务层整体启动（同 A 域 2.1）：

```powershell
cd E:\pyidea\LeaseGuardian\java-service
mvn spring-boot:run
```

新增依赖（pom.xml）：
- `spring-security-crypto`（BCrypt，版本由 Spring Boot 管理）
- `jjwt-api / jjwt-impl / jjwt-jackson` 0.12.6（impl/jackson 为 runtime）
- `spring-boot-starter-validation`（参数校验。**超出指令官"仅 crypto 与 jjwt"约束，已经总协调人批准豁免**）

JWT 密钥：yml `leaseguardian.jwt.secret-key`，Base64、解码后 ≥ 32 字节（`openssl rand -base64 64`）。**禁止把真实密钥提交进 git**，生产走环境变量。

---

## 3. B 域核心接口

统一约定（对 D 域尤为重要）：
- 全部走 `Result<T>` 壳：`{code, msg, data, request_id}`，**唯一成功标准是 `code === "A00000"`，不是 HTTP 200**
- 全局 SNAKE_CASE：多词字段下划线（`room_no`、`monthly_rent`、`user_id`、`request_id`）
- 需登录的接口统一从 Header 取凭证：`Authorization: Bearer <JWT>`
- `request_id` 仅异常路径填充，成功响应恒为 null
- 时间字段是 ISO-8601 字符串（`"2026-10-26"` / `"2026-10-26T11:00:00.000"`），**不是时间戳**

### 3.1 注册 — `POST /auth/register`（无需 token）

```json
{ "username": "zhangsan", "password": "12345678", "room_no": "302" }
```

规则：
- 三者均必填（空 → A00001）
- `room_no` 必须恰好 3 位纯数字（`^\d{3}$`，如 `302` ✓、`3a2` ✗）
- 用户名重复 → A04003；房间已被入住（存在 ACTIVE/TERMINATING 租约）→ A04004

成功 data：

```json
{ "message": "入住成功", "room_no": "302", "monthly_rent": 800.00, "deposit": 1600.00 }
```

注意：**响应不含 user_id**，需要 user_id 请走登录接口。

### 3.2 登录 — `POST /auth/login`（无需 token）

```json
{ "username": "zhangsan", "password": "12345678" }
```

成功 data：

```json
{ "token": "<JWT>", "user_id": 1, "username": "zhangsan" }
```

- token 有效期 24h，HS512 签名，claims 含 `userId` / `username` / `role`
- **用户不存在与密码错误统一返回 A04005**，不区分，防账号枚举；前端不要提示"用户不存在"

### 3.3 当前用户 + 租约摘要 — `GET /auth/me`（需 token）

```http
Authorization: Bearer <JWT>
```

成功 data：

```json
{
  "user_id": 1, "username": "zhangsan", "room_no": "302",
  "monthly_rent": 800.00, "deposit": 1600.00,
  "start_date": "2026-10-24", "end_date": "2027-04-24",
  "status": "ACTIVE"
}
```

- 租约状态枚举：`ACTIVE / TERMINATING / TERMINATED / EXPIRED`
- **对外契约**：A 域 Python 登录态识别依赖本接口，变更需周知 A

### 3.4 按 id 查用户 — `GET /auth/users/{id}`（需 token）

成功 data：`{ "id": 1, "username": "zhangsan", "room_no": "302", "role": "TENANT", "phone": null, "created_at": "..." }`
说明：最小闭环未做越权校验，任何登录用户可查任意 id，前端不得依赖此行为。

---

## 4. 鉴权机制（B 域底座，跨域复用）

- `JwtTokenInterceptor` 挂载范围（`WebConfig`）：`/auth/**`（放行 `/auth/login`、`/auth/register`）+ `/api/chat/**`
- Service 层取当前用户：`BaseContext.getCurrentUserId()`，无需接触 token
- token 缺失/无效/过期 → 拦截器统一抛 `A00010` / 401，Controller/Service 零感知
- `/tickets`、`/chat`（Python 编排入口）刻意不在拦截范围，**不破坏 A 域链路**
- 业务归属校验（如"只能查自己的会话"）在各自域内做，用 `BaseContext.getCurrentUserId()` 比对，参考 A 域历史接口实现

---

## 5. 数据表说明

### B 域主表

```text
user        -- 注意: MySQL 保留字, SQL/注解中一律 `user` 带反引号
lease
```

`user` 核心字段：`id` / `username`(唯一) / `password_hash`(BCrypt) / `room_no` / `role` / `phone`(可空) / `created_at` / `updated_at`

`lease` 核心字段：`id` / `tenant_id`(逻辑关联 user.id，无物理外键) / `start_date` / `end_date` / `monthly_rent` / `deposit` / `status` / `move_out_date` / `terminated_at` / `active_flag`

`active_flag` 机制：MySQL 生成列，`status ∈ (ACTIVE, TERMINATING)` 时为 1，否则 NULL；配合唯一索引 `uk_tenant_active(tenant_id, active_flag)` 实现"一人一张生效租约"，NULL 不参与唯一冲突，退租后可插入新租约。**实体不映射该字段**。

DDL 见 `sql/V2__user_lease.sql`（第 3 段 `repair_ticket` 迁移属 A 域，已另出 `V2.1__repair_ticket_tenant_id.sql`）。

---

## 6. 错误码（B 域）

账号域独立编号 **A04**（A00 保持纯通用域，这是总协调人已拍板冻结的规范）：

| code | HTTP | 含义 |
|---|---|---|
| A04001 | 400 | 房间号格式非法（须 3 位纯数字） |
| A04003 | 409 | 用户名已存在 |
| A04004 | 409 | 该房间已有人入住 |
| A04005 | 401 | 用户名或密码错误（统一报错） |

复用通用域：A00001 参数校验失败 / A00002 用户不存在 / A00010 未登录或 token 无效。

---

## 7. B 域验收清单

- [ ] 注册成功返回 `入住成功` + 租约摘要（room_no/monthly_rent/deposit）
- [ ] `room_no=3a2` → A04001 / 400
- [ ] 重复用户名 → A04003 / 409；同房再注册 → A04004 / 409
- [ ] 密码错误 → A04005 / 401（与不存在的用户返回一致）
- [ ] 登录返回 JWT，带 token 访问 `/auth/me` 返回用户 + 租约摘要
- [ ] 不带 token / 乱改 token → A00010 / 401
- [ ] 数据库 `password_hash` 为 `$2a$10$...` 开头 BCrypt 串，无明文
- [ ] 撞房失败后 `user`/`lease` 无残留（单事务回滚）

---

## 8. 已完成 / 未做 / TODO

### 已完成
注册、登录、`/auth/me`、`/auth/users/{id}`、JWT 签发与校验、拦截器与 `BaseContext`、`user`/`lease` 建表、A04 错误码、全局参数校验出口

### 明确未做（本期需求外）
- token 吊销 / 强制下线 / 改密踢人（无黑名单机制）
- 登录限流 / 验证码（按指令官约束不实现）
- 手机号登录 / 短信验证
- 房间维度唯一约束（"一房一人"绝对保证，当前仅有应用层预检，极端并发有窗口）

### TODO（待 C 裁决的灰点）
- 成功响应是否填充 requestId（当前恒 null）
- 时间序列化格式是否统一为 `yyyy-MM-dd HH:mm:ss`（当前 ISO-8601）
- 上述裁决结果请 C 更新进总规范

---

## 9. B 域边界声明

B 域后续只维护：
- `/auth/**` 账号域接口与 JWT 鉴权底座
- `user` / `lease` 表及其 DDL
- `BaseContext` / 拦截器 / `WebConfig` 的鉴权路径注册

common 层（`Result` / `ErrorCode` / `GlobalExceptionHandler`）为跨域共享，B 域改动前需全员周知。

不主动修改：
- A 域工单 / 会话 / Python 编排
- C 域退租业务
- D 域前端实现

**对外硬契约**：`POST /auth/login` 与 `GET /auth/me` 的响应结构（token / user_id / 租约摘要字段），A 域 Python 与 D 域前端均直接消费，变更必须先通知。

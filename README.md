# LeaseGuardian 智能租赁管家

LeaseGuardian 是一个练手项目，目标是打通“租客入住 → 报修 → 退租结算”的核心链路。

## 当前状态

项目已完成第一阶段核心闭环：

- 账号域：注册 / 登录 / JWT
- 报修域：报修、查工单、维修责任与价格咨询
- 退租域：退租申请、搬离日、损坏登记、结算、确认 / 取消
- RAG：维修条款与退租条款共用同一套检索底座
- 会话管理：session、历史消息、短期记忆 v1
- 前端：Vue3 + TypeScript，已接入核心对话流程

## 架构分工

- A：报修工单域 + Python 编排层公共底座
- B：账号域 / 登录 / JWT
- C：退租域 / checkout 主流程 / 统一出口流式改造
- D：前端

## 分域文档

- [A 域：报修工单与编排层](docs/A-agent-and-ticket-domain.md)
- [B 域：账号与登录](docs/B-auth-domain.md)
- [C 域：退租与 checkout](docs/C-checkout-domain.md)
- [D 域：前端说明](docs/D-frontend.md)

## 启动顺序

### 1. 启动 Java 业务层

```powershell
cd java-service
mvn spring-boot:run
```

### 2. 启动 Python 编排层

```powershell
cd agent-service
.\.venv\Scripts\Activate.ps1
uvicorn agent_service.main:app --host 127.0.0.1 --port 8000
```

### 3. 启动前端

见 `docs/D-frontend.md`

## 核心入口

- 前端入口：见 D 域文档
- Python 编排入口：`POST /chat`
- Java 业务层：见各域文档

## 当前已知边界

- 不是生产级完整产品，是核心链路练手项目
- 长期记忆、多租户、复杂权限、部署运维未做
- 会话与记忆属于 v1，仅覆盖短期上下文
- 正式演示前建议清理测试数据

## 下一步建议

- 做最终目录统一
- 补 `.env.example` / `requirements.txt`
- 做一次演示数据初始化脚本

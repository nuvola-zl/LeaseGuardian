CREATE DATABASE IF NOT EXISTS leaseguardian
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE leaseguardian;

DROP TABLE IF EXISTS repair_ticket;

CREATE TABLE repair_ticket (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  tenant_id VARCHAR(64) NOT NULL COMMENT '租客ID',
  description VARCHAR(1000) NOT NULL COMMENT '报修描述',
  status VARCHAR(32) NOT NULL DEFAULT 'REGISTERED' COMMENT '工单状态码：REGISTERED=已登记',
  related_lease_id BIGINT UNSIGNED NULL COMMENT '关联租约ID：预留字段，当前不填',
  request_id VARCHAR(64) NULL COMMENT '幂等请求号：防LLM重复调用产生重复工单；NULL不参与唯一冲突',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_repair_ticket_request_id (request_id),
  KEY idx_repair_ticket_tenant_id (tenant_id),
  KEY idx_repair_ticket_status (status),
  KEY idx_repair_ticket_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='租客报修工单表';

-- ============================================================
-- V2__user_lease.sql
-- LeaseGuardian 账号与租约域建表脚本
-- 数据库: leaseguardian
-- 说明:
--   1. lease.tenant_id -> user.id 为逻辑外键, 不加物理 FOREIGN KEY, 一致性由代码保证
--   2. user / lease 表字段以此文件为准, 勿随意增删列
--   3. user 是 MySQL 8.0 保留字, 表名全程必须带反引号
-- ============================================================

USE `leaseguardian`;

-- ------------------------------------------------------------
-- 1. 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`      VARCHAR(64)     NOT NULL                COMMENT '登录用户名',
  `password_hash` VARCHAR(128)    NOT NULL                COMMENT '密码哈希(BCrypt)',
  `room_no`       VARCHAR(32)     NOT NULL                COMMENT '房间号, 3位纯数字',
  `role`          VARCHAR(16)     NOT NULL DEFAULT 'TENANT' COMMENT '角色: TENANT/LANDLORD/ADMIN',
  `phone`         VARCHAR(32)     DEFAULT NULL            COMMENT '手机号',
  `created_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_room_no` (`room_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. 租约表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `lease` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '租约ID',
  `tenant_id`     BIGINT UNSIGNED NOT NULL                COMMENT '租客用户ID, 逻辑关联 user.id',
  `start_date`    DATE            NOT NULL                COMMENT '起租日',
  `end_date`      DATE            NOT NULL                COMMENT '到期日',
  `monthly_rent`  DECIMAL(10,2)   NOT NULL                COMMENT '月租金',
  `deposit`       DECIMAL(10,2)   NOT NULL                COMMENT '押金',
  `status`        VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE' COMMENT '租约状态: ACTIVE/TERMINATING/TERMINATED/EXPIRED',
  `move_out_date` DATE            DEFAULT NULL            COMMENT '租客申请搬离日, 退租流程启动时写入',
  `terminated_at` DATETIME(3)     DEFAULT NULL            COMMENT '退租流程完成时间',
  `active_flag`   TINYINT GENERATED ALWAYS AS
                  (CASE WHEN `status` IN ('ACTIVE','TERMINATING') THEN 1 ELSE NULL END) VIRTUAL
                  COMMENT '生效标记: 生效租约为 1, 否则为 NULL',
  `created_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (`id`),
  -- "一人一张生效租约" 数据库级约束:
  --   active_flag 为 NULL 的行不参与唯一键冲突; 只有 ACTIVE / TERMINATING 状态的
  --   租约 active_flag=1, 同一 tenant_id 出现第二张生效租约会撞唯一键;
  --   退租后 active_flag 变为 NULL, 该租客可正常插入新租约。
  UNIQUE KEY `uk_tenant_active` (`tenant_id`, `active_flag`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租约表';

-- ------------------------------------------------------------
-- 3. repair_ticket.tenant_id 类型迁移 (工单域, 仅出 SQL, 不动其业务代码)
--    ⚠️ 应用代码中 repair_ticket 实体的 tenantId 类型需由工单域负责人
--       同步修改: String -> Long (本文件不负责业务代码变更)
-- ------------------------------------------------------------
-- 迁移前置自检: 先执行下面语句, 确认结果为 0 再跑 ALTER。
-- 若 tenant_id 存在 NULL 或非纯数字的存量数据, ALTER 在严格模式下会直接报错。
--   SELECT COUNT(*) FROM repair_ticket
--   WHERE tenant_id IS NULL OR tenant_id NOT REGEXP '^[0-9]+$';
ALTER TABLE `repair_ticket`
  MODIFY COLUMN `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租客用户ID, 逻辑关联 user.id';






USE leaseguardian;

-- =========================================================
-- 1. 退租单
-- =========================================================
CREATE TABLE checkout_case (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租客ID，逻辑指向 user.id',
    lease_id BIGINT NOT NULL COMMENT '租约ID，逻辑指向 lease.id',
    request_id VARCHAR(64) NOT NULL COMMENT '幂等/链路号，全局唯一',
    status VARCHAR(20) NOT NULL COMMENT 'APPLYING/AWAITING_CONFIRM/COMPLETED/CANCELLED',
    move_out_date DATE NULL COMMENT '计划搬离日；出结算前必须非空',
    settlement_bill_id BIGINT NULL COMMENT '结算账单ID，逻辑指向 bill.id',
    settlement_version INT NOT NULL DEFAULT 0 COMMENT '结算版本，确认必须匹配当前版本',
    expected_refund_amount DECIMAL(12,2) NULL COMMENT '结算快照：应退总额',
    has_pending_damage TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否存在待人工损坏：1阻塞最终确认',
    completed_at DATETIME NULL COMMENT '完成时间',
    cancelled_at DATETIME NULL COMMENT '取消时间',
    version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    active_case_flag BIGINT
        GENERATED ALWAYS AS (
            CASE WHEN status IN ('APPLYING','AWAITING_CONFIRM') THEN 1 ELSE NULL END
        ) STORED COMMENT '未完结退租单标记：1表示活跃，NULL表示终态',

    PRIMARY KEY (id),
    UNIQUE KEY uk_checkout_request (request_id),
    UNIQUE KEY uk_checkout_active_case (tenant_id, active_case_flag),
    KEY idx_checkout_lease_status (lease_id, status),
    KEY idx_checkout_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='退租单';


-- =========================================================
-- 2. 损坏项
-- =========================================================
CREATE TABLE damage_item (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    case_id BIGINT NOT NULL COMMENT '退租单ID，逻辑指向 checkout_case.id',
    tenant_id BIGINT NOT NULL COMMENT '租客ID，逻辑指向 user.id',
    item_name VARCHAR(64) NOT NULL COMMENT '损坏物品名，如：浴缸',
    description VARCHAR(255) NULL COMMENT '损坏描述',
    responsibility VARCHAR(20) NOT NULL COMMENT 'TENANT人为赔/NATURAL_WEAR自然老化/MANUAL_PENDING待人工',
    review_status VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUIRED' COMMENT 'NOT_REQUIRED/PENDING/RESOLVED',
    reference_amount DECIMAL(12,2) NULL COMMENT 'AI参考价；待人工为NULL',
    final_amount DECIMAL(12,2) NULL COMMENT '人工核定最终金额；未核定为NULL',
    basis_doc_id VARCHAR(64) NULL COMMENT '责任判定条款来源',
    basis_clause_no VARCHAR(32) NULL COMMENT '条款号',
    basis_excerpt VARCHAR(512) NULL COMMENT '条款摘录快照',
    request_id VARCHAR(64) NULL COMMENT '登记幂等号，可空但唯一',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    PRIMARY KEY (id),
    UNIQUE KEY uk_damage_request (request_id),
    KEY idx_damage_case (case_id),
    KEY idx_damage_tenant (tenant_id),
    CONSTRAINT chk_damage_amount CHECK (reference_amount IS NULL OR reference_amount >= 0),
    CONSTRAINT chk_damage_final_amount CHECK (final_amount IS NULL OR final_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='退租损坏项';


-- =========================================================
-- 3. 账单头
-- =========================================================
CREATE TABLE bill (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租客ID，逻辑指向 user.id',
    lease_id BIGINT NOT NULL COMMENT '租约ID，逻辑指向 lease.id',
    case_id BIGINT NULL COMMENT '退租单ID；UTILITY_DEBT可空，SETTLEMENT_REFUND必填',
    request_id VARCHAR(64) NOT NULL COMMENT '出单幂等号，全局唯一',
    bill_type VARCHAR(20) NOT NULL COMMENT 'UTILITY_DEBT水电欠费/SETTLEMENT_REFUND退租结算退款',
    period_month CHAR(7) NULL COMMENT '水电账期YYYY-MM；结算单为NULL',
    direction VARCHAR(12) NOT NULL COMMENT 'RECEIVABLE租客欠/REFUND退给租客',
    amount DECIMAL(12,2) NOT NULL COMMENT '头金额：结算单=Σ退款项-Σ扣款项',
    status VARCHAR(16) NOT NULL COMMENT 'OPEN/CLOSED/CANCELLED',
    source VARCHAR(12) NOT NULL DEFAULT 'SYSTEM' COMMENT 'SYSTEM/MANUAL',
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    PRIMARY KEY (id),
    UNIQUE KEY uk_bill_request (request_id),
    KEY idx_bill_tenant_lease (tenant_id, lease_id),
    KEY idx_bill_case (case_id),
    KEY idx_bill_type_period (bill_type, period_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='账单头';


-- =========================================================
-- 4. 账单/结算明细
-- =========================================================
CREATE TABLE bill_item (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
    bill_id BIGINT NOT NULL COMMENT '账单ID，逻辑指向 bill.id',
    line_no INT NOT NULL COMMENT '行号',
    item_code VARCHAR(32) NOT NULL COMMENT 'DEPOSIT_REFUND/UNUSED_RENT/UTILITY_DEBT/DAMAGE_COMPENSATION',
    item_name VARCHAR(64) NOT NULL COMMENT '展示名',
    direction VARCHAR(12) NOT NULL COMMENT 'RECEIVABLE/REFUND',
    amount DECIMAL(12,2) NOT NULL COMMENT '本行金额，非负',
    months INT NULL COMMENT 'UNUSED_RENT专用：剩余整月数',
    monthly_rent DECIMAL(12,2) NULL COMMENT 'UNUSED_RENT专用：月租快照',
    formula_snapshot VARCHAR(255) NULL COMMENT '公式快照，如 max(0,(202610-202606)-1)*800',
    basis_doc_id VARCHAR(64) NOT NULL COMMENT '条款依据',
    basis_clause_no VARCHAR(32) NOT NULL COMMENT '条款号',
    basis_excerpt VARCHAR(512) NOT NULL COMMENT '条款摘录',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    PRIMARY KEY (id),
    UNIQUE KEY uk_bill_item_line (bill_id, line_no),
    KEY idx_bill_item_bill (bill_id),
    CONSTRAINT chk_bill_item_amount CHECK (amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='账单/结算明细';




USE leaseguardian;

CREATE TABLE IF NOT EXISTS chat_session (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID，逻辑关联 user.id',
  scene VARCHAR(16) NOT NULL COMMENT '业务入口：REPAIR=报修/工单，CHECKOUT=租约/退租/结算',
  title VARCHAR(128) NOT NULL COMMENT '会话标题，前端会话列表展示',
  summary TEXT NULL COMMENT '会话摘要；用于老历史压缩后的上下文恢复，不是完整历史',
  state_json JSON NULL COMMENT '会话级临时状态，业务状态以业务表为唯一真相源，可重建',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_chat_session_user_scene (user_id, scene),
  KEY idx_chat_session_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

CREATE TABLE IF NOT EXISTS chat_message (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息ID',
  session_id BIGINT UNSIGNED NOT NULL COMMENT '会话ID，逻辑关联 chat_session.id',
  seq INT NOT NULL COMMENT '会话内消息序号，从1开始递增',
  role VARCHAR(16) NOT NULL COMMENT '消息角色：USER=用户，ASSISTANT=助手',
  content TEXT NOT NULL COMMENT '消息内容',
  metadata_json JSON NULL COMMENT '扩展元数据：scene/ticket_id/case_id等',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_chat_message_session_seq (session_id, seq),
  KEY idx_chat_message_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息历史表';
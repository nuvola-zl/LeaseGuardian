package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 租约表实体
 * 注意: active_flag 是 MySQL 生成列 (一人一张生效租约的数据库级约束),
 * 由数据库自动维护, 实体不映射该字段, INSERT/UPDATE 均不触碰它
 */
@Data
@TableName("lease")
public class Lease {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 租客用户ID, 逻辑关联 user.id, 无物理外键 */
    private Long tenantId;

    private LocalDate startDate;

    private LocalDate endDate;

    private BigDecimal monthlyRent;

    private BigDecimal deposit;

    /** 租约状态: ACTIVE / TERMINATING / TERMINATED / EXPIRED */
    private String status;

    /** 租客申请搬离日, 退租流程启动时写入 */
    private LocalDate moveOutDate;

    /** 退租流程完成时间 */
    private LocalDateTime terminatedAt;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}

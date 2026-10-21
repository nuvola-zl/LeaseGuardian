package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("checkout_case")
public class CheckoutCase {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private Long leaseId;
    private String requestId;
    private String status;
    private LocalDate moveOutDate;
    private Long settlementBillId;
    private Integer settlementVersion;
    private BigDecimal expectedRefundAmount;
    private Boolean hasPendingDamage;
    private LocalDateTime completedAt;
    private LocalDateTime cancelledAt;
    private Integer version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
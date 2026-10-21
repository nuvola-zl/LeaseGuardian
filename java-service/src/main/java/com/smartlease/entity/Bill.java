package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("bill")
public class Bill {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private Long leaseId;
    private Long caseId;
    private String requestId;
    private String billType;
    private String periodMonth;
    private String direction;
    private BigDecimal amount;
    private String status;
    private String source;
    private LocalDateTime generatedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("damage_item")
public class DamageItem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long caseId;
    private Long tenantId;
    private String itemName;
    private String description;
    private String responsibility;
    private String reviewStatus;
    private BigDecimal referenceAmount;
    private BigDecimal finalAmount;
    private String basisDocId;
    private String basisClauseNo;
    private String basisExcerpt;
    private String requestId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
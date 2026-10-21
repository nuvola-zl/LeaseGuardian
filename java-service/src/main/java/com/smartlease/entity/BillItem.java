package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("bill_item")
public class BillItem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long billId;
    private Integer lineNo;
    private String itemCode;
    private String itemName;
    private String direction;
    private BigDecimal amount;
    private Integer months;
    private BigDecimal monthlyRent;
    private String formulaSnapshot;
    private String basisDocId;
    private String basisClauseNo;
    private String basisExcerpt;
    private LocalDateTime createdAt;
}
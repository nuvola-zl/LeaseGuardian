package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("repair_ticket")
public class RepairTicket {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long tenantId;

    private String description;

    /**
     * 数据库存英文码 REGISTERED；展示中文在返回层处理。
     */
    private String status;

    /**
     * 预留字段，本期不填。
     */
    private Long relatedLeaseId;

    /**
     * 幂等请求号；可空，唯一索引 uk_repair_ticket_request_id。
     */
    private String requestId;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
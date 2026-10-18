package com.smartlease.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 当前登录用户 + 租约摘要视图
 * 供 Python 身份工具 get_current_user() 消费
 * 出站时驼峰字段自动转下划线 (SNAKE_CASE 策略): user_id, room_no, monthly_rent, start_date ...
 */
@Data
@Builder
public class MeResponseVO {

    private Long userId;

    private String username;

    private String roomNo;

    /** 租约摘要: 注册即开通, 正常情况必有; 防御性允许为 null */
    private BigDecimal monthlyRent;

    private BigDecimal deposit;

    private LocalDate startDate;

    private LocalDate endDate;

    /** 租约状态: ACTIVE / TERMINATING / TERMINATED / EXPIRED */
    private String status;
}
package com.smartlease.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

/**
 * 注册结果: 入住成功 + 初始租约信息
 */
@Data
@Builder
public class RegisterResultVO {

    private String message;

    private String roomNo;

    private BigDecimal monthlyRent;

    private BigDecimal deposit;
}

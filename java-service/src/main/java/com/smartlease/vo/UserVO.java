package com.smartlease.vo;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户信息视图对象, 绝不携带 passwordHash
 */
@Data
@Builder
public class UserVO {

    private Long id;

    private String username;

    private String roomNo;

    private String role;

    private String phone;

    private LocalDateTime createdAt;
}

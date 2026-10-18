package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户表实体
 * 注意: user 是 MySQL 8.0 保留字, @TableName 必须带反引号
 * 字段口径以 sql/V2__user_lease.sql 为准, 勿随意增删
 */
@Data
@TableName("`user`")
public class User {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String username;

    private String passwordHash;

    /** 房间号, 3 位纯数字 */
    private String roomNo;

    /** 角色: TENANT / LANDLORD / ADMIN */
    private String role;

    private String phone;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}

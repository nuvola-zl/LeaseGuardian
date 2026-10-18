package com.smartlease.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class RegisterRequest {

    private String username;

    private String password;

    /**
     * 房间号, 3 位纯数字
     * 项目全局 Jackson SNAKE_CASE 策略: JSON key 为下划线风格 (room_no)
     */
    @JsonProperty("room_no")
    private String roomNo;
}
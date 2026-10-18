package com.smartlease.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class LoginResponseVO {

    private String token;

    private Long userId;

    private String username;
}

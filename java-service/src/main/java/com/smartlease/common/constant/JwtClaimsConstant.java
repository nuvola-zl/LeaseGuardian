package com.smartlease.common.constant;

/**
 * JWT claims 常量, 避免魔法字符串散落各处
 * 口径: userId / username / role 三个 claims, 由登录时签发
 */
public class JwtClaimsConstant {

    public static final String USER_ID = "userId";
    public static final String USERNAME = "username";
    public static final String ROLE = "role";

    private JwtClaimsConstant() {
    }
}

package com.smartlease.service;


import com.smartlease.dto.LoginRequest;
import com.smartlease.dto.RegisterRequest;
import com.smartlease.vo.LoginResponseVO;
import com.smartlease.vo.MeResponseVO;
import com.smartlease.vo.RegisterResultVO;
import com.smartlease.vo.UserVO;

public interface AuthService {

    RegisterResultVO register(RegisterRequest request);

    LoginResponseVO login(LoginRequest request);

    UserVO getUserById(Long id);

    /** 当前登录用户 + 租约摘要, userId 由 JWT 拦截器写入 BaseContext */
    MeResponseVO getCurrentUser();
}

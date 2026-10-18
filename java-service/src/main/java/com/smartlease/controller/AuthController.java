package com.smartlease.controller;


import com.smartlease.common.result.Result;
import com.smartlease.dto.LoginRequest;
import com.smartlease.dto.RegisterRequest;
import com.smartlease.service.AuthService;
import com.smartlease.vo.LoginResponseVO;
import com.smartlease.vo.MeResponseVO;
import com.smartlease.vo.RegisterResultVO;
import com.smartlease.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 账号域接口
 * 除 /auth/login、/auth/register 外, /auth/** 其余路径需携带 Bearer token (见 WebConfig)
 */
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Validated
public class AuthController {

    private final AuthService authService;

    /** 注册: 开户 + 开通初始租约, 单事务 */
    @PostMapping("/register")
    public Result<RegisterResultVO> register(@Validated @RequestBody RegisterRequest request) {
        return Result.success(authService.register(request));
    }

    /** 登录: 校验密码, 签发 JWT */
    @PostMapping("/login")
    public Result<LoginResponseVO> login(@Validated @RequestBody LoginRequest request) {
        return Result.success(authService.login(request));
    }

    /** 根据 ID 查询用户信息 (需要 token, 演示登录校验闭环) */
    @GetMapping("/users/{id}")
    public Result<UserVO> getUserById(@PathVariable("id") Long id) {
        return Result.success(authService.getUserById(id));
    }

    /** 当前登录用户 + 租约摘要 (Python 身份工具 get_current_user 专用, 需要 token) */
    @GetMapping("/me")
    public Result<MeResponseVO> me() {
        return Result.success(authService.getCurrentUser());
    }
}

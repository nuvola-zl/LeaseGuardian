package com.smartlease.common.config;

import com.smartlease.common.interceptor.JwtTokenInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置: 注册 JWT 拦截器
 *
 * 拦截范围说明:
 * - /auth/** 需要登录, 但放行 /auth/login、/auth/register (登录注册本身不能要 token);
 * - /api/chat/** 前端聊天历史查询 (工单域接口, 鉴权由本拦截器统一提供);
 * - /tickets、/chat 等工单/聊天链路不在拦截范围内, 避免影响 Python /chat 调用。
 */
@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final JwtTokenInterceptor jwtTokenInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtTokenInterceptor)
                .addPathPatterns("/auth/**", "/api/chat/**")
                .excludePathPatterns("/auth/login", "/auth/register");
    }
}
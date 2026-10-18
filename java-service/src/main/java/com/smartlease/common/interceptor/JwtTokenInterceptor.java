package com.smartlease.common.interceptor;

import com.smartlease.common.code.ErrorCode;
import com.smartlease.common.constant.JwtClaimsConstant;
import com.smartlease.common.context.BaseContext;
import com.smartlease.common.exception.BusinessException;
import com.smartlease.common.properties.JwtProperties;
import com.smartlease.common.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 统一 JWT 认证拦截器
 *
 * 设计决策:
 * 1. 校验失败抛 BusinessException(UNAUTHORIZED, 401), 走 GlobalExceptionHandler
 *    统一封装 Result, HTTP 语义与统一返回壳两不误;
 * 2. 只拦截 /auth/** 且放行 /auth/login、/auth/register (见 WebConfig),
 *    工单链路 /tickets 不带 token, 刻意不覆盖, 不影响报修域闭环。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtTokenInterceptor implements HandlerInterceptor {

    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtProperties jwtProperties;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        // 静态资源等非处理器方法直接放行
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }

        String header = request.getHeader("Authorization");
        if (header == null || !header.startsWith(BEARER_PREFIX)) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "未携带登录凭证", HttpStatus.UNAUTHORIZED);
        }

        String token = header.substring(BEARER_PREFIX.length());
        try {
            Claims claims = JwtUtil.parseJWT(jwtProperties.getSecretKey(), token);
            Long userId = Long.valueOf(claims.get(JwtClaimsConstant.USER_ID).toString());
            String username = claims.get(JwtClaimsConstant.USERNAME, String.class);
            String role = claims.get(JwtClaimsConstant.ROLE, String.class);
            BaseContext.setCurrentUser(userId, username, role);
            log.debug("JWT 校验通过: userId={}, username={}", userId, username);
            return true;
        } catch (Exception e) {
            // 过期 / 签名不对 / 结构损坏统一一种错误, 不细分原因
            log.warn("JWT 校验失败: {}", e.getMessage());
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "登录凭证无效或已过期", HttpStatus.UNAUTHORIZED);
        }
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        BaseContext.removeCurrentUser();
    }
}

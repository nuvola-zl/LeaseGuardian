package com.smartlease.common.context;

/**
 * 当前登录用户上下文 (ThreadLocal)
 * 由 JwtTokenInterceptor 在每次请求开始时写入, 请求结束时清理
 */
public class BaseContext {

    /** 当前登录用户快照 */
    public record CurrentUser(Long userId, String username, String role) {
    }

    private static final ThreadLocal<CurrentUser> THREAD_LOCAL = new ThreadLocal<>();

    public static void setCurrentUser(Long userId, String username, String role) {
        THREAD_LOCAL.set(new CurrentUser(userId, username, role));
    }

    public static CurrentUser getCurrentUser() {
        return THREAD_LOCAL.get();
    }

    public static Long getCurrentUserId() {
        CurrentUser user = THREAD_LOCAL.get();
        return user == null ? null : user.userId();
    }

    public static void removeCurrentUser() {
        THREAD_LOCAL.remove();
    }

    private BaseContext() {
    }
}

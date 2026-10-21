package com.smartlease.dto;

/**
 * 创建工单入参。
 * 全局 Jackson SNAKE_CASE 下，前端传 tenant_id / description / request_id。
 */
public record TicketCreateRequest(
        Long tenantId,
        String description,
        String requestId
) {
}
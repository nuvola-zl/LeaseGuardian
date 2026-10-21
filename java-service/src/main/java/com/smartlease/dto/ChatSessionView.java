package com.smartlease.dto;

import java.time.LocalDateTime;

public record ChatSessionView(
        Long sessionId,
        String title,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
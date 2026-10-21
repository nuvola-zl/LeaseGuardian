package com.smartlease.dto;

import java.time.LocalDateTime;

public record ChatMessageView(
        String role,
        String content,
        LocalDateTime createdAt
) {
}
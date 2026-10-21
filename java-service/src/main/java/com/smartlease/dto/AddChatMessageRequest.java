package com.smartlease.dto;

public record AddChatMessageRequest(
        String role,
        String content,
        String metadataJson
) {
}
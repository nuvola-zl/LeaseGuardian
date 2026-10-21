package com.smartlease.controller;


import com.smartlease.common.context.BaseContext;
import com.smartlease.common.exception.BusinessException;
import com.smartlease.common.result.Result;
import com.smartlease.dto.*;
import com.smartlease.entity.ChatMessage;
import com.smartlease.entity.ChatSession;
import com.smartlease.service.ChatSessionService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatSessionService chatSessionService;

    @PostMapping("/sessions")
    public Result<ChatSession> createSession(
            @RequestParam Long userId,
            @RequestBody CreateChatSessionRequest req
    ) {
        return Result.success(chatSessionService.create(userId, req));
    }

    @GetMapping("/sessions")
    public Result<List<ChatSession>> listSessions(
            @RequestParam Long userId,
            @RequestParam(required = false) String scene
    ) {
        return Result.success(chatSessionService.listSessions(userId, scene));
    }

    @PostMapping("/sessions/{sessionId}/messages")
    public Result<ChatMessage> addMessage(
            @PathVariable Long sessionId,
            @RequestBody AddChatMessageRequest req
    ) {
        return Result.success(chatSessionService.addMessage(sessionId, req));
    }

    @GetMapping("/sessions/{sessionId}/messages")
    public Result<List<ChatMessage>> listMessages(@PathVariable Long sessionId) {
        return Result.success(chatSessionService.listMessages(sessionId));
    }

    @GetMapping("/sessions/{sessionId}")
    public Result<ChatSession> getSession(@PathVariable Long sessionId) {
        return Result.success(chatSessionService.getById(sessionId));
    }

    @PatchMapping("/sessions/{sessionId}/state")
    public Result<ChatSession> updateSessionState(
            @PathVariable Long sessionId,
            @RequestBody UpdateChatSessionStateRequest req
    ) {
        return Result.success(chatSessionService.updateState(sessionId, req.stateJson()));
    }

    @GetMapping("/api/chat/sessions/{sessionId}/messages")
    public Result<List<ChatMessageView>> listMessagesForFrontend(
            @PathVariable Long sessionId
    ) {
        Long currentUserId = BaseContext.getCurrentUserId();

        ChatSession session = chatSessionService.findById(sessionId);
        if (session == null || !session.getUserId().equals(currentUserId)) {
            throw BusinessException.forbidden("无权访问该会话");
        }

        return Result.success(chatSessionService.listMessageViews(sessionId));
    }

    @GetMapping("/api/chat/sessions")
    public Result<List<ChatSessionView>> listSessionsForFrontend(
            @RequestParam String scene
    ) {
        Long currentUserId = BaseContext.getCurrentUserId();
        return Result.success(chatSessionService.listSessionViews(currentUserId, scene, 50));
    }
}
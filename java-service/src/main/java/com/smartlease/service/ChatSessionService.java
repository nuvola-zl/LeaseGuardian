package com.smartlease.service;



import com.smartlease.dto.AddChatMessageRequest;
import com.smartlease.dto.ChatMessageView;
import com.smartlease.dto.ChatSessionView;
import com.smartlease.dto.CreateChatSessionRequest;
import com.smartlease.entity.ChatMessage;
import com.smartlease.entity.ChatSession;

import java.util.List;

public interface ChatSessionService {

    ChatSession create(Long userId, CreateChatSessionRequest req);

    ChatMessage addMessage(Long sessionId, AddChatMessageRequest req);

    List<ChatMessage> listMessages(Long sessionId);

    List<ChatSession> listSessions(Long userId, String scene);

    ChatSession getById(Long sessionId);

    ChatSession updateState(Long sessionId, String stateJson);

    ChatSession findById(Long sessionId);

    List<ChatMessageView> listMessageViews(Long sessionId);

    List<ChatSessionView> listSessionViews(
            Long userId,
            String scene,
            int limit
    );
}
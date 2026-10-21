package com.smartlease.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
;
import com.smartlease.common.code.ErrorCode;
import com.smartlease.common.exception.BusinessException;
import com.smartlease.dto.AddChatMessageRequest;
import com.smartlease.dto.ChatMessageView;
import com.smartlease.dto.ChatSessionView;
import com.smartlease.dto.CreateChatSessionRequest;
import com.smartlease.entity.ChatMessage;
import com.smartlease.entity.ChatSession;
import com.smartlease.mapper.ChatMessageMapper;
import com.smartlease.mapper.ChatSessionMapper;
import com.smartlease.service.ChatSessionService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ChatSessionServiceImpl implements ChatSessionService {

    private final ChatSessionMapper chatSessionMapper;
    private final ChatMessageMapper chatMessageMapper;

    @Override
    public ChatSession create(Long userId, CreateChatSessionRequest req) {
        if (userId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "userId is required");
        }
        if (req == null || !StringUtils.hasText(req.scene())) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "scene is required");
        }

        String scene = req.scene().trim().toUpperCase();
        if (!scene.equals("REPAIR") && !scene.equals("CHECKOUT")) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "scene must be REPAIR or CHECKOUT");
        }

        String title = StringUtils.hasText(req.title())
                ? req.title().trim()
                : ("REPAIR".equals(scene) ? "新报修会话" : "新退租会话");

        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setScene(scene);
        session.setTitle(title);
        chatSessionMapper.insert(session);
        return session;
    }

    @Override
    public ChatMessage addMessage(Long sessionId, AddChatMessageRequest req) {
        if (sessionId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "sessionId is required");
        }
        if (req == null || !StringUtils.hasText(req.role()) || !StringUtils.hasText(req.content())) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "role and content are required");
        }

        Long count = chatMessageMapper.selectCount(
                Wrappers.<ChatMessage>lambdaQuery()
                        .eq(ChatMessage::getSessionId, sessionId)
        );

        ChatMessage message = new ChatMessage();
        message.setSessionId(sessionId);
        message.setSeq(count == null ? 1 : count.intValue() + 1);
        message.setRole(req.role().trim().toUpperCase());
        message.setContent(req.content());
        message.setMetadataJson(req.metadataJson());

        chatMessageMapper.insert(message);
        return message;
    }

    @Override
    public List<ChatMessage> listMessages(Long sessionId) {
        if (sessionId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "sessionId is required");
        }
        return chatMessageMapper.selectList(
                Wrappers.<ChatMessage>lambdaQuery()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .orderByAsc(ChatMessage::getSeq)
        );
    }

    @Override
    public List<ChatSession> listSessions(Long userId, String scene) {
        if (userId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "userId is required");
        }
        var wrapper = Wrappers.<ChatSession>lambdaQuery()
                .eq(ChatSession::getUserId, userId)
                .orderByDesc(ChatSession::getUpdatedAt);
        if (StringUtils.hasText(scene)) {
            wrapper.eq(ChatSession::getScene, scene.trim().toUpperCase());
        }
        return chatSessionMapper.selectList(wrapper);
    }

    @Override
    public ChatSession getById(Long sessionId) {
        if (sessionId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "sessionId is required");
        }
        ChatSession session = chatSessionMapper.selectById(sessionId);
        if (session == null) {
            throw BusinessException.notFound(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "chat session not found: " + sessionId
            );
        }
        return session;
    }

    @Override
    public ChatSession findById(Long sessionId) {
        if (sessionId == null) {
            return null;
        }
        return chatSessionMapper.selectById(sessionId);
    }

    @Override
    public List<ChatMessageView> listMessageViews(Long sessionId) {
        return listMessages(sessionId).stream()
                .map(m -> new ChatMessageView(
                        m.getRole(),
                        m.getContent(),
                        m.getCreatedAt()
                ))
                .toList();
    }

    @Override
    public List<ChatSessionView> listSessionViews(
            Long userId,
            String scene,
            int limit
    ) {
        if (userId == null) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "userId is required");
        }
        if (!org.springframework.util.StringUtils.hasText(scene)) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "scene is required");
        }

        String sceneNorm = scene.trim().toUpperCase();
        if (!sceneNorm.equals("REPAIR") && !sceneNorm.equals("CHECKOUT")) {
            throw BusinessException.badRequest(ErrorCode.PARAM_ERROR, "scene must be REPAIR or CHECKOUT");
        }

        var wrapper = Wrappers.<ChatSession>lambdaQuery()
                .eq(ChatSession::getUserId, userId)
                .eq(ChatSession::getScene, sceneNorm)
                .orderByDesc(ChatSession::getUpdatedAt);

        com.baomidou.mybatisplus.extension.plugins.pagination.Page<ChatSession> page =
                new com.baomidou.mybatisplus.extension.plugins.pagination.Page<>(1, limit);

        chatSessionMapper.selectPage(page, wrapper);

        return page.getRecords().stream()
                .map(this::toSessionView)
                .toList();
    }

    private ChatSessionView toSessionView(ChatSession session) {
        String title = session.getTitle();
        if (!org.springframework.util.StringUtils.hasText(title)) {
            title = loadFirstUserMessageBrief(session.getId());
        }
        return new ChatSessionView(
                session.getId(),
                title,
                session.getCreatedAt(),
                session.getUpdatedAt()
        );
    }

    private String loadFirstUserMessageBrief(Long sessionId) {
        ChatMessage first = chatMessageMapper.selectOne(
                Wrappers.<ChatMessage>lambdaQuery()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .eq(ChatMessage::getRole, "USER")
                        .orderByAsc(ChatMessage::getSeq)
                        .last("limit 1")
        );
        if (first == null || !org.springframework.util.StringUtils.hasText(first.getContent())) {
            return "新会话";
        }

        String content = first.getContent().trim().replaceAll("\\s+", " ");
        return content.length() > 20 ? content.substring(0, 20) + "..." : content;
    }

    @Override
    public ChatSession updateState(Long sessionId, String stateJson) {
        ChatSession session = getById(sessionId);
        session.setStateJson(stateJson);
        chatSessionMapper.updateById(session);
        return getById(sessionId);
    }
}
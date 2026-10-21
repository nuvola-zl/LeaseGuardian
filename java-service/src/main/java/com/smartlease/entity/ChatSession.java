package com.smartlease.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("chat_session")
public class ChatSession {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String scene;

    private String title;

    private String summary;

    private String stateJson;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
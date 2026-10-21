package com.smartlease.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import com.smartlease.entity.ChatMessage;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ChatMessageMapper extends BaseMapper<ChatMessage> {
}
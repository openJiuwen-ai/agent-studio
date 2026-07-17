/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.memory;

import com.openjiuwen.studio.agent.common.dto.agent.Message;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import org.apache.commons.collections4.CollectionUtils;

import java.util.ArrayList;
import java.util.List;

/**
 * 一轮对话的信息
 *
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserCachedChatTurn {
    private long lastUpdateTime;

    private List<Message> messages;

    public UserCachedChatTurn(List<Message> messages) {
        this.lastUpdateTime = System.currentTimeMillis();
        this.messages = messages;
    }

    /**
     * 轮次内添加消息
     *
     * @param message message
     */
    public void addMessage(Message message) {
        if (message == null) {
            return;
        }

        if (this.messages == null) {
            this.messages = new ArrayList<>();
        }

        this.messages.add(message);
        this.lastUpdateTime = System.currentTimeMillis();
    }

    /**
     * 轮次内批量添加消息
     *
     * @param messages messages
     */
    public void addMessages(List<Message> messages) {
        if (CollectionUtils.isEmpty(messages)) {
            return;
        }

        if (this.messages == null) {
            this.messages = new ArrayList<>();
        }

        this.messages.addAll(messages);
        this.lastUpdateTime = System.currentTimeMillis();
    }
}

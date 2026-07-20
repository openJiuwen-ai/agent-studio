/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model;

import com.openjiuwen.studio.agent.common.dto.agent.Message;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * Conversation model for Redis storage, matching runtime format.
 */
@Data
public class Conversation {
    private long lastUpdateTime = System.currentTimeMillis();
    private List<Message> messageList = new ArrayList<>();
    private boolean old;
    private long dialogueCount = 1;

    public void addDialogueCount() {
        ++dialogueCount;
    }
}
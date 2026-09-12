/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.conversation.application.dto;

import lombok.Getter;

import java.util.List;

@Getter
public final class ConversationSkillContext {
    private final List<ConversationSkillDescriptor> catalog;
    private final List<String> recommendedSkillIds;

    public ConversationSkillContext(List<ConversationSkillDescriptor> catalog, List<String> recommendedSkillIds) {
        this.catalog = List.copyOf(catalog);
        this.recommendedSkillIds = List.copyOf(recommendedSkillIds);
    }

    public static ConversationSkillContext empty() {
        return new ConversationSkillContext(List.of(), List.of());
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.conversation.application.dto;

import lombok.Builder;
import lombok.Value;

@Value
@Builder
public class ConversationSkillDescriptor {
    String skillId;
    String versionId;
    String name;
    String description;
    String objectKey;
}

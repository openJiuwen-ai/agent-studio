/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.model.valueobject;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Token 用量值对象（对齐 ModelApiLog）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TokenUsage {
    private String promptTokens;

    private String completionTokens;

    private String totalTokens;
}

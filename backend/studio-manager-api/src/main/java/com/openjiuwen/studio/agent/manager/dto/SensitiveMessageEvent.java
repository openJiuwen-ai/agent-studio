/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Getter;
import lombok.Setter;

/**
 * 敏感词消息块结构
 *
 */
@Setter
@Getter
public class SensitiveMessageEvent extends MessageEvent {
    @JsonProperty("offset")
    private int offset;
}

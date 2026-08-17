/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

/**
 * 创建 openjiuwen 知识库请求。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenCreateKBReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("kb_id")
    private String kbId;

    @JsonProperty("kb_name")
    private String kbName;

    private Map<String, Object> metadata;

    @JsonProperty("model_config")
    private KBModelConfig modelConfig;
}

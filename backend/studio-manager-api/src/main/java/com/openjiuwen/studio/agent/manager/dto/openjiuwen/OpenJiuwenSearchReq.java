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

/**
 * 检索 openjiuwen 知识库请求。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenSearchReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("kb_id")
    private String kbId;

    private String query;

    @JsonProperty("top_k")
    private Integer topK;

    @JsonProperty("index_type")
    private String indexType;

    @JsonProperty("model_config")
    private KBModelConfig modelConfig;
}

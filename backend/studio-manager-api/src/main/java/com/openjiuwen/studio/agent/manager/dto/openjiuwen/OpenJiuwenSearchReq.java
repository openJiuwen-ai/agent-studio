/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
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
    @Schema(description = "知识库ID", example = "kb-001")
    private String kbId;

    @Schema(description = "检索查询语句", example = "如何配置Agent")
    private String query;

    @JsonProperty("top_k")
    @Schema(description = "返回结果数量", example = "5")
    private Integer topK;

    @JsonProperty("index_type")
    @Schema(description = "索引类型", example = "vector")
    private String indexType;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "{}")
    private KBModelConfig modelConfig;
}

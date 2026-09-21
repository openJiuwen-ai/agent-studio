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

import java.util.Map;

/**
 * 创建 openjiuwen 知识库请求。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenCreateKBReq {

    @JsonProperty("kb_id")
    @Schema(description = "知识库ID", example = "kb-001")
    private String kbId;

    @JsonProperty("kb_name")
    @Schema(description = "知识库名称", example = "产品知识库")
    private String kbName;

    @Schema(description = "元数据", example = "{}")
    private Map<String, Object> metadata;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "{}")
    private KBModelConfig modelConfig;
}

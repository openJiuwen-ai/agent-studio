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
 * Embedding 模型配置（通过模型中心解析）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KBModelConfig implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("model_service_id")
    private String modelServiceId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("project_id")
    @Builder.Default
    private String projectId = "0";

    @JsonProperty("auth_id")
    @Builder.Default
    private String authId = "";
}

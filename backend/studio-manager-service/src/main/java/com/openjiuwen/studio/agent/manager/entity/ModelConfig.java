/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Builder;
import lombok.Data;

/**
 * 功能描述
 *
 */
@Data
@Builder
public class ModelConfig {
    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("hyper_parameters")
    private HyperParameters hyperParameters;

    private Extension extension;
}

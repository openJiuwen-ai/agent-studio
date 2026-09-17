/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.jiuwen.models;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * SchemaConfig配置类型
 *
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
@Builder
public class SchemaConfig {
    private String type;

    private String location;

    private String description;

    @JsonProperty("validated")
    private boolean shouldValidate;

    @JsonProperty("validate_type")
    private String validateType;

    @JsonProperty("validate_rule")
    private String validateRule;

    @JsonProperty("default")
    private String defaultValue;

    @JsonProperty("env_var_ref")
    private String envVarRef;

    private Map<String, SchemaConfig> properties;

    private SchemaConfig items;

    private List<String> required;

    private List<SchemaConfig> oneOf;
}

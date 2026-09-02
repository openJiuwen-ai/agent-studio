/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class ContextDTO {

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name;

    @JsonProperty("value_before")
    @Schema(description = "变更前的值", example = "示例字符串")
    private String valueBefor;

    @JsonProperty("value_after")
    @Schema(description = "变更后的值", example = "示例字符串")
    private String valueAfter;
}

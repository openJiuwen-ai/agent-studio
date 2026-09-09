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

import java.util.List;
import java.util.Map;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class RoundDTO {

    @JsonProperty("context_list")
    @Schema(description = "上下文列表", example = "[]")
    private List<ContextDTO> contextList;

    @JsonProperty("workflow_list")
    @Schema(description = "工作流列表", example = "[]")
    private List<WorkFlowDTO> workflowList;

    @JsonProperty("module_input")
    @Schema(description = "模块输入", example = "{}")
    private Map<String, Object> moduleInput;

    @JsonProperty("module_output")
    @Schema(description = "模块输出", example = "{}")
    private Map<String, Object> moduleOutput;

    @Schema(description = "索引序号", example = "0")
    private int index;

    @Schema(description = "错误节点信息", example = "{}")
    private com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo errorNode;
}

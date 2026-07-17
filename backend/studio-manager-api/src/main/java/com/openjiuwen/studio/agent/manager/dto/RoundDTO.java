/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

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
    private List<ContextDTO> contextList;

    @JsonProperty("workflow_list")
    private List<WorkFlowDTO> workflowList;

    @JsonProperty("module_input")
    private Map<String, Object> moduleInput;

    @JsonProperty("module_output")
    private Map<String, Object> moduleOutput;

    private int index;

    private com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo errorNode;
}

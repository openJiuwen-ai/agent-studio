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
public class WorkFlowDTO {

    @Schema(description = "工作流ID", example = "wf-001")
    private String id;

    @Schema(description = "执行时机", example = "pre")
    private String timing;

    @Schema(description = "领域对象名称", example = "agent")
    private String domainObjectName;

    @JsonProperty("context_list")
    @Schema(description = "上下文", example = "示例字符串")
    private Map<String, ContextDTO> contextList;

    @JsonProperty("event_list")
    @Schema(description = "事件列表", example = "[]")
    private List<com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo> eventList;

    @Schema(description = "索引序号", example = "0")
    private int index;

    @Schema(description = "错误信息", example = "节点执行失败")
    private String errorMessage;

    @Schema(description = "工作流状态", example = "completed")
    private com.openjiuwen.studio.agent.common.dto.agent.Status status;
}

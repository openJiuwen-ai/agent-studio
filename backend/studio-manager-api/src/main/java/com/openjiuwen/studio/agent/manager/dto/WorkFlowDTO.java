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
public class WorkFlowDTO {

    private String id;

    private String timing;

    private String domainObjectName;

    @JsonProperty("context_list")
    private Map<String, ContextDTO> contextList;

    @JsonProperty("event_list")
    private List<com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo> eventList;

    private int index;

    private String errorMessage;

    private com.openjiuwen.studio.agent.common.dto.agent.Status status;
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 智能体最新版本列表响应体。
 */
@ApiModel(description = "智能体最新版本列表响应体。")

@Validated

public class AgentVersionListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("agent_version_list")
    @Schema(description = "Agent版本列表", example = "[]")
    @Valid
    @Size()
    private List<AgentVersionListItem> agentVersionList = null;

    public Long getCount() {
        return count;
    }

    public AgentVersionListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<AgentVersionListItem> getAgentVersionList() {
        return agentVersionList;
    }

    public AgentVersionListRsp setAgentVersionList(List<AgentVersionListItem> agentVersionList) {
        this.agentVersionList = agentVersionList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentVersionListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    agentVersionList: ").append(toIndentedString(agentVersionList)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        AgentVersionListRsp agentVersionListRsp = (AgentVersionListRsp) o;
        return Objects.equals(this.count, agentVersionListRsp.count) && Objects.equals(this.agentVersionList,
            agentVersionListRsp.agentVersionList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, agentVersionList);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}

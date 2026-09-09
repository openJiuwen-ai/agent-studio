/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识型Agent执行请求体。
 */
@ApiModel(description = "知识型Agent执行请求体。")

@Validated

public class AgentRunReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("query")
    @Schema(description = "查询内容", example = "查询内容示例", required = true)
    @NotBlank
    @Length(min = 1, max = 8192)
    private String query = null;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1")
    private Long version = null;

    @JsonProperty("long_term_memory")
    @Schema(description = "长期记忆", example = "1")
    @Valid
    private LongTermMemoryRuntime longTermMemory = null;

    public String getQuery() {
        return query;
    }

    public AgentRunReq setQuery(String query) {
        this.query = query;
        return this;
    }

    public Long getVersion() {
        return version;
    }

    public AgentRunReq setVersion(Long version) {
        this.version = version;
        return this;
    }

    public LongTermMemoryRuntime getLongTermMemory() {
        return longTermMemory;
    }

    public AgentRunReq setLongTermMemory(LongTermMemoryRuntime longTermMemory) {
        this.longTermMemory = longTermMemory;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentRunReq {\n");

        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    longTermMemory: ").append(toIndentedString(longTermMemory)).append("\n");
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
        AgentRunReq agentRunReq = (AgentRunReq) o;
        return Objects.equals(this.query, agentRunReq.query) && Objects.equals(this.version, agentRunReq.version)
            && Objects.equals(this.longTermMemory, agentRunReq.longTermMemory);
    }

    @Override
    public int hashCode() {
        return Objects.hash(query, version, longTermMemory);
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

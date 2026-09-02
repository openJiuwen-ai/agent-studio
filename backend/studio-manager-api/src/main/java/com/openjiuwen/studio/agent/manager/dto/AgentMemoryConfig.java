/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 记忆相关的配置。
 */
@ApiModel(description = "记忆相关的配置。")

@Validated

public class AgentMemoryConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("memory_repo_id")
    @Schema(description = "记忆仓库ID", example = "mem_repo_001")
    @Length(max = 64)
    private String memoryRepoId = null;

    @JsonProperty("name")
    @Schema(description = "记忆配置名称", example = "用户记忆")
    @Length(min = 1, max = 50)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "记忆配置描述", example = "存储用户偏好和历史对话记忆")
    @Length(max = 1000)
    private String description = null;

    public String getMemoryRepoId() {
        return memoryRepoId;
    }

    public AgentMemoryConfig setMemoryRepoId(String memoryRepoId) {
        this.memoryRepoId = memoryRepoId;
        return this;
    }

    public String getName() {
        return name;
    }

    public AgentMemoryConfig setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AgentMemoryConfig setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentMemoryConfig {\n");

        sb.append("    memoryRepoId: ").append(toIndentedString(memoryRepoId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        AgentMemoryConfig agentMemoryConfig = (AgentMemoryConfig) o;
        return Objects.equals(this.memoryRepoId, agentMemoryConfig.memoryRepoId) && Objects.equals(this.name,
            agentMemoryConfig.name) && Objects.equals(this.description, agentMemoryConfig.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memoryRepoId, name, description);
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

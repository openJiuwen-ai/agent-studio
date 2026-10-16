/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 记忆配置的IR对象。
 */
@ApiModel(description = "记忆配置的IR对象。")

@Validated

public class MemoryConfigIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("memory_repo_id")
    @Schema(description = "记忆库ID", example = "memory-repo-001")
    private String memoryRepoId = null;

    @JsonProperty("extract_config")
    @Schema(description = "提取触发配置", example = "{\"max_chat_turn\":10,\"time_window\":3600}")
    private ExtractConfig extractConfig = null;

    @JsonProperty("strategies")
    @Schema(description = "长期记忆策略列表", example = "[{\"type\":\"summary\"}]")
    private List<LongTermMemoryStrategy> strategies = null;

    /**
     * 是否启用 LLM 节点的记忆注入。绑定记忆库时应置 true。
     */
    @JsonProperty("enable")
    @Schema(description = "是否启用记忆注入", example = "true")
    private Boolean enable = null;

    /**
     * 记忆后端类型：BUILTIN（内置）/EXTERNAL（外部agent-memory）。
     * 运行态据此分支派发：EXTERNAL 走 ExternalMemoryClient，BUILTIN 走现有 get_ltm()。
     */
    @JsonProperty("memory_backend_type")
    @Schema(description = "记忆后端类型", example = "BUILTIN")
    private String memoryBackendType = null;

    /**
     * 记忆库scope_id（= memory_repo_id），agent-memory 用此做隔离。
     */
    @JsonProperty("scope_id")
    @Schema(description = "记忆库scope_id", example = "memory-repo-001")
    private String scopeId = null;

    /**
     * 外部记忆服务实例ID（EXTERNAL时由IR携带，runtime按此从OBS auth文件惰性取api_key）。
     * 非敏感引用，不含api_key本身。
     */
    @JsonProperty("instance_id")
    @Schema(description = "外部记忆服务实例ID", example = "instance-001")
    private String instanceId = null;

    /**
     * 外部记忆服务实例base_url（EXTERNAL时由IR携带，runtime直连agent-memory）。
     */
    @JsonProperty("instance_base_url")
    @Schema(description = "外部记忆服务实例地址", example = "http://mem-svc-a:8000")
    private String instanceBaseUrl = null;

    public String getMemoryRepoId() {
        return memoryRepoId;
    }

    public MemoryConfigIR setMemoryRepoId(String memoryRepoId) {
        this.memoryRepoId = memoryRepoId;
        return this;
    }

    public ExtractConfig getExtractConfig() {
        return extractConfig;
    }

    public MemoryConfigIR setExtractConfig(ExtractConfig extractConfig) {
        this.extractConfig = extractConfig;
        return this;
    }

    public List<LongTermMemoryStrategy> getStrategies() {
        return strategies;
    }

    public MemoryConfigIR setStrategies(List<LongTermMemoryStrategy> strategies) {
        this.strategies = strategies;
        return this;
    }

    public Boolean getEnable() {
        return enable;
    }

    public MemoryConfigIR setEnable(Boolean enable) {
        this.enable = enable;
        return this;
    }

    public String getMemoryBackendType() {
        return memoryBackendType;
    }

    public MemoryConfigIR setMemoryBackendType(String memoryBackendType) {
        this.memoryBackendType = memoryBackendType;
        return this;
    }

    public String getScopeId() {
        return scopeId;
    }

    public MemoryConfigIR setScopeId(String scopeId) {
        this.scopeId = scopeId;
        return this;
    }

    public String getInstanceId() {
        return instanceId;
    }

    public MemoryConfigIR setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    public String getInstanceBaseUrl() {
        return instanceBaseUrl;
    }

    public MemoryConfigIR setInstanceBaseUrl(String instanceBaseUrl) {
        this.instanceBaseUrl = instanceBaseUrl;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryConfigIR {\n");
        sb.append("    memoryRepoId: ").append(toIndentedString(memoryRepoId)).append("\n");
        sb.append("    extractConfig: ").append(toIndentedString(extractConfig)).append("\n");
        sb.append("    strategies: ").append(toIndentedString(strategies)).append("\n");
        sb.append("    enable: ").append(toIndentedString(enable)).append("\n");
        sb.append("    memoryBackendType: ").append(toIndentedString(memoryBackendType)).append("\n");
        sb.append("    scopeId: ").append(toIndentedString(scopeId)).append("\n");
        sb.append("    instanceId: ").append(toIndentedString(instanceId)).append("\n");
        sb.append("    instanceBaseUrl: ").append(toIndentedString(instanceBaseUrl)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(java.lang.Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        MemoryConfigIR memoryConfigIR = (MemoryConfigIR) o;
        return Objects.equals(this.memoryRepoId, memoryConfigIR.memoryRepoId)
            && Objects.equals(this.extractConfig, memoryConfigIR.extractConfig)
            && Objects.equals(this.strategies, memoryConfigIR.strategies)
            && Objects.equals(this.enable, memoryConfigIR.enable)
            && Objects.equals(this.memoryBackendType, memoryConfigIR.memoryBackendType)
            && Objects.equals(this.scopeId, memoryConfigIR.scopeId)
            && Objects.equals(this.instanceId, memoryConfigIR.instanceId)
            && Objects.equals(this.instanceBaseUrl, memoryConfigIR.instanceBaseUrl);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memoryRepoId, extractConfig, strategies, enable,
            memoryBackendType, scopeId, instanceId, instanceBaseUrl);
    }

    private String toIndentedString(java.lang.Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }

    /**
     * 提取触发配置，对应 Python IR 中的 configs.memory.extractConfig。
     */
    public static class ExtractConfig implements Serializable {
        private static final long serialVersionUID = 1L;

        @JsonProperty("max_chat_turn")
        @Schema(description = "最大对话轮次", example = "10")
        private Integer maxChatTurn = null;

        @JsonProperty("time_window")
        @Schema(description = "时间窗口（秒）", example = "3600")
        private Integer timeWindow = null;

        public Integer getMaxChatTurn() {
            return maxChatTurn;
        }

        public ExtractConfig setMaxChatTurn(Integer maxChatTurn) {
            this.maxChatTurn = maxChatTurn;
            return this;
        }

        public Integer getTimeWindow() {
            return timeWindow;
        }

        public ExtractConfig setTimeWindow(Integer timeWindow) {
            this.timeWindow = timeWindow;
            return this;
        }

        @Override
        public boolean equals(java.lang.Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            ExtractConfig that = (ExtractConfig) o;
            return Objects.equals(this.maxChatTurn, that.maxChatTurn)
                && Objects.equals(this.timeWindow, that.timeWindow);
        }

        @Override
        public int hashCode() {
            return Objects.hash(maxChatTurn, timeWindow);
        }

        @Override
        public String toString() {
            return "ExtractConfig{maxChatTurn=" + maxChatTurn + ", timeWindow=" + timeWindow + "}";
        }
    }
}

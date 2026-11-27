/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * FEAT-134 MCP 导入/重载操作结果（受理快照与终态查询共用）。
 *
 * 受理返回 HTTP 202 时 status=RUNNING、各 item 为 PENDING；
 * 终态 status ∈ SUCCESS / PARTIAL_SUCCESS / FAILED / INTERRUPTED。
 * created_count 与 success_count 分开：success 仅表示目标工具刷新成功。
 */
public class McpTransferOperationResp {

    public static final String TYPE_IMPORT = "IMPORT";
    public static final String TYPE_RELOAD = "RELOAD";

    public static final String STATUS_RUNNING = "RUNNING";
    public static final String STATUS_SUCCESS = "SUCCESS";
    public static final String STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS";
    public static final String STATUS_FAILED = "FAILED";
    public static final String STATUS_INTERRUPTED = "INTERRUPTED";

    @JsonProperty("operation_id")
    private String operationId;

    @JsonProperty("operation_type")
    private String operationType;

    @JsonProperty("status")
    private String status;

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("created_count")
    private Integer createdCount;

    @JsonProperty("success_count")
    private Integer successCount;

    @JsonProperty("failed_count")
    private Integer failedCount;

    @JsonProperty("service_id")
    private String serviceId;

    @JsonProperty("items")
    private List<Item> items;

    @JsonProperty("safe_reason")
    private String safeReason;

    /**
     * 逐项结果（导入项或单服务重载结果）。
     */
    public static class Item {
        @JsonProperty("index")
        private Integer index;

        @JsonProperty("service_id")
        private String serviceId;

        @JsonProperty("original_name")
        private String originalName;

        @JsonProperty("name")
        private String name;

        @JsonProperty("status")
        private String status;

        @JsonProperty("created")
        private Boolean created;

        @JsonProperty("refresh_status")
        private String refreshStatus;

        @JsonProperty("tool_count")
        private Integer toolCount;

        @JsonProperty("previous_tool_count")
        private Integer previousToolCount;

        @JsonProperty("added_count")
        private Integer addedCount;

        @JsonProperty("removed_count")
        private Integer removedCount;

        @JsonProperty("added_tools")
        private List<String> addedTools;

        @JsonProperty("removed_tools")
        private List<String> removedTools;

        @JsonProperty("changed_tools")
        private List<String> changedTools;

        @JsonProperty("requires_auth_configuration")
        private Boolean requiresAuthConfiguration;

        @JsonProperty("requires_republish")
        private Boolean requiresRepublish;

        @JsonProperty("pending_config_paths")
        private List<String> pendingConfigPaths;

        @JsonProperty("error_code")
        private String errorCode;

        @JsonProperty("reason")
        private String reason;

        public Integer getIndex() {
            return index;
        }

        public Item setIndex(Integer index) {
            this.index = index;
            return this;
        }

        public String getServiceId() {
            return serviceId;
        }

        public Item setServiceId(String serviceId) {
            this.serviceId = serviceId;
            return this;
        }

        public String getOriginalName() {
            return originalName;
        }

        public Item setOriginalName(String originalName) {
            this.originalName = originalName;
            return this;
        }

        public String getName() {
            return name;
        }

        public Item setName(String name) {
            this.name = name;
            return this;
        }

        public String getStatus() {
            return status;
        }

        public Item setStatus(String status) {
            this.status = status;
            return this;
        }

        public Boolean getCreated() {
            return created;
        }

        public Item setCreated(Boolean created) {
            this.created = created;
            return this;
        }

        public String getRefreshStatus() {
            return refreshStatus;
        }

        public Item setRefreshStatus(String refreshStatus) {
            this.refreshStatus = refreshStatus;
            return this;
        }

        public Integer getToolCount() {
            return toolCount;
        }

        public Item setToolCount(Integer toolCount) {
            this.toolCount = toolCount;
            return this;
        }

        public Integer getPreviousToolCount() {
            return previousToolCount;
        }

        public Item setPreviousToolCount(Integer previousToolCount) {
            this.previousToolCount = previousToolCount;
            return this;
        }

        public Integer getAddedCount() {
            return addedCount;
        }

        public Item setAddedCount(Integer addedCount) {
            this.addedCount = addedCount;
            return this;
        }

        public Integer getRemovedCount() {
            return removedCount;
        }

        public Item setRemovedCount(Integer removedCount) {
            this.removedCount = removedCount;
            return this;
        }

        public List<String> getAddedTools() {
            return addedTools;
        }

        public Item setAddedTools(List<String> addedTools) {
            this.addedTools = addedTools;
            return this;
        }

        public List<String> getRemovedTools() {
            return removedTools;
        }

        public Item setRemovedTools(List<String> removedTools) {
            this.removedTools = removedTools;
            return this;
        }

        public List<String> getChangedTools() {
            return changedTools;
        }

        public Item setChangedTools(List<String> changedTools) {
            this.changedTools = changedTools;
            return this;
        }

        public Boolean getRequiresAuthConfiguration() {
            return requiresAuthConfiguration;
        }

        public Item setRequiresAuthConfiguration(Boolean requiresAuthConfiguration) {
            this.requiresAuthConfiguration = requiresAuthConfiguration;
            return this;
        }

        public Boolean getRequiresRepublish() {
            return requiresRepublish;
        }

        public Item setRequiresRepublish(Boolean requiresRepublish) {
            this.requiresRepublish = requiresRepublish;
            return this;
        }

        public List<String> getPendingConfigPaths() {
            return pendingConfigPaths;
        }

        public Item setPendingConfigPaths(List<String> pendingConfigPaths) {
            this.pendingConfigPaths = pendingConfigPaths;
            return this;
        }

        public String getErrorCode() {
            return errorCode;
        }

        public Item setErrorCode(String errorCode) {
            this.errorCode = errorCode;
            return this;
        }

        public String getReason() {
            return reason;
        }

        public Item setReason(String reason) {
            this.reason = reason;
            return this;
        }
    }

    public String getOperationId() {
        return operationId;
    }

    public McpTransferOperationResp setOperationId(String operationId) {
        this.operationId = operationId;
        return this;
    }

    public String getOperationType() {
        return operationType;
    }

    public McpTransferOperationResp setOperationType(String operationType) {
        this.operationType = operationType;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public McpTransferOperationResp setStatus(String status) {
        this.status = status;
        return this;
    }

    public Integer getTotal() {
        return total;
    }

    public McpTransferOperationResp setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public Integer getCreatedCount() {
        return createdCount;
    }

    public McpTransferOperationResp setCreatedCount(Integer createdCount) {
        this.createdCount = createdCount;
        return this;
    }

    public Integer getSuccessCount() {
        return successCount;
    }

    public McpTransferOperationResp setSuccessCount(Integer successCount) {
        this.successCount = successCount;
        return this;
    }

    public Integer getFailedCount() {
        return failedCount;
    }

    public McpTransferOperationResp setFailedCount(Integer failedCount) {
        this.failedCount = failedCount;
        return this;
    }

    public String getServiceId() {
        return serviceId;
    }

    public McpTransferOperationResp setServiceId(String serviceId) {
        this.serviceId = serviceId;
        return this;
    }

    public List<Item> getItems() {
        return items;
    }

    public McpTransferOperationResp setItems(List<Item> items) {
        this.items = items;
        return this;
    }

    public String getSafeReason() {
        return safeReason;
    }

    public McpTransferOperationResp setSafeReason(String safeReason) {
        this.safeReason = safeReason;
        return this;
    }
}

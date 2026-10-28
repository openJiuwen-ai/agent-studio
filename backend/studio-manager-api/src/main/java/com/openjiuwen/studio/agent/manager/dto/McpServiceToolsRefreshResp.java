/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * MCP 服务工具列表重载结果
 */
@Schema(description = "MCP 服务工具列表重载结果")
public class McpServiceToolsRefreshResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp-001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "天气查询服务")
    private String name = null;

    @JsonProperty("fc_instance_status")
    @Schema(description = "重载后的服务状态", example = "success")
    private String fcInstanceStatus = null;

    @JsonProperty("tools")
    @Schema(description = "重载后的工具清单（JSON字符串，格式与工具列表查询接口一致）")
    private String tools = null;

    @JsonProperty("total")
    @Schema(description = "重载后的工具总数（含保留的已下线工具）", example = "5")
    private Integer total = 0;

    @JsonProperty("added_count")
    @Schema(description = "新增工具数量", example = "1")
    private Integer addedCount = 0;

    @JsonProperty("removed_count")
    @Schema(description = "下线工具数量", example = "0")
    private Integer removedCount = 0;

    @JsonProperty("updated_count")
    @Schema(description = "变更工具数量", example = "0")
    private Integer updatedCount = 0;

    @JsonProperty("added")
    @Schema(description = "新增工具清单")
    private List<McpToolDiffItem> added = new ArrayList<>();

    @JsonProperty("removed")
    @Schema(description = "下线工具清单，referenced 为 true 时表示仍被引用并以已下线状态保留")
    private List<McpToolDiffItem> removed = new ArrayList<>();

    @JsonProperty("updated")
    @Schema(description = "变更工具清单")
    private List<McpToolDiffItem> updated = new ArrayList<>();

    public String getId() {
        return id;
    }

    public McpServiceToolsRefreshResp setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceToolsRefreshResp setName(String name) {
        this.name = name;
        return this;
    }

    public String getFcInstanceStatus() {
        return fcInstanceStatus;
    }

    public McpServiceToolsRefreshResp setFcInstanceStatus(String fcInstanceStatus) {
        this.fcInstanceStatus = fcInstanceStatus;
        return this;
    }

    public String getTools() {
        return tools;
    }

    public McpServiceToolsRefreshResp setTools(String tools) {
        this.tools = tools;
        return this;
    }

    public Integer getTotal() {
        return total;
    }

    public McpServiceToolsRefreshResp setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public Integer getAddedCount() {
        return addedCount;
    }

    public McpServiceToolsRefreshResp setAddedCount(Integer addedCount) {
        this.addedCount = addedCount;
        return this;
    }

    public Integer getRemovedCount() {
        return removedCount;
    }

    public McpServiceToolsRefreshResp setRemovedCount(Integer removedCount) {
        this.removedCount = removedCount;
        return this;
    }

    public Integer getUpdatedCount() {
        return updatedCount;
    }

    public McpServiceToolsRefreshResp setUpdatedCount(Integer updatedCount) {
        this.updatedCount = updatedCount;
        return this;
    }

    public List<McpToolDiffItem> getAdded() {
        return added;
    }

    public McpServiceToolsRefreshResp setAdded(List<McpToolDiffItem> added) {
        this.added = added;
        return this;
    }

    public List<McpToolDiffItem> getRemoved() {
        return removed;
    }

    public McpServiceToolsRefreshResp setRemoved(List<McpToolDiffItem> removed) {
        this.removed = removed;
        return this;
    }

    public List<McpToolDiffItem> getUpdated() {
        return updated;
    }

    public McpServiceToolsRefreshResp setUpdated(List<McpToolDiffItem> updated) {
        this.updated = updated;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        McpServiceToolsRefreshResp that = (McpServiceToolsRefreshResp) o;
        return Objects.equals(id, that.id) && Objects.equals(name, that.name) && Objects.equals(fcInstanceStatus,
            that.fcInstanceStatus) && Objects.equals(tools, that.tools) && Objects.equals(total, that.total)
            && Objects.equals(addedCount, that.addedCount) && Objects.equals(removedCount, that.removedCount)
            && Objects.equals(updatedCount, that.updatedCount) && Objects.equals(added, that.added)
            && Objects.equals(removed, that.removed) && Objects.equals(updated, that.updated);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, fcInstanceStatus, tools, total, addedCount, removedCount, updatedCount, added,
            removed, updated);
    }

    @Override
    public String toString() {
        return "McpServiceToolsRefreshResp{" + "id='" + id + '\'' + ", name='" + name + '\'' + ", fcInstanceStatus='"
            + fcInstanceStatus + '\'' + ", total=" + total + ", addedCount=" + addedCount + ", removedCount="
            + removedCount + ", updatedCount=" + updatedCount + ", added=" + added + ", removed=" + removed
            + ", updated=" + updated + '}';
    }
}

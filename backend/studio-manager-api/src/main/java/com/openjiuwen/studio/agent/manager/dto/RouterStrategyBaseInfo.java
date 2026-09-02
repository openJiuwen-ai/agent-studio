/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * RouterStrategyBaseInfo
 */

@Validated

public class RouterStrategyBaseInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "路由策略ID", example = "strategy-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    private String id = null;

    @JsonProperty("strategy_key")
    @Schema(description = "策略键", example = "route_key_001")
    private String strategyKey = null;

    @JsonProperty("strategy_name")
    @Schema(description = "策略名称", example = "默认路由策略")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5a-zA-Z0-9_. |/:\\\\-]{1,35}$")
    private String strategyName = null;

    @JsonProperty("strategy_description")
    @Schema(description = "策略描述", example = "默认的路由策略")
    private String strategyDescription = null;

    @JsonProperty("service_list")
    @Schema(description = "服务列表", example = "[]")
    @Valid
    @Size()
    private List<ModelServiceRsp> serviceList = null;

    @JsonProperty("domain_id")
    @Schema(description = "域ID", example = "domain-123")
    private String domainId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    private String workspaceId = null;

    @JsonProperty("created_by_user_name")
    @Schema(description = "创建者用户名", example = "张三")
    private String createdByUserName = null;

    @JsonProperty("created_date")
    @Schema(description = "创建日期时间戳", example = "1709251200000")
    private Long createdDate = null;

    @JsonProperty("last_updated_date")
    @Schema(description = "最后更新日期时间戳", example = "1709337600000")
    private Long lastUpdatedDate = null;

    @JsonProperty("strategy_timeout")
    @Schema(description = "策略超时时间（毫秒）", example = "30000")
    private Integer strategyTimeout = null;

    @JsonProperty("strategy_retry_count")
    @Schema(description = "策略重试次数", example = "3")
    private Integer strategyRetryCount = null;

    public String getId() {
        return id;
    }

    public RouterStrategyBaseInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getStrategyKey() {
        return strategyKey;
    }

    public RouterStrategyBaseInfo setStrategyKey(String strategyKey) {
        this.strategyKey = strategyKey;
        return this;
    }

    public String getStrategyName() {
        return strategyName;
    }

    public RouterStrategyBaseInfo setStrategyName(String strategyName) {
        this.strategyName = strategyName;
        return this;
    }

    public String getStrategyDescription() {
        return strategyDescription;
    }

    public RouterStrategyBaseInfo setStrategyDescription(String strategyDescription) {
        this.strategyDescription = strategyDescription;
        return this;
    }

    public List<ModelServiceRsp> getServiceList() {
        return serviceList;
    }

    public RouterStrategyBaseInfo setServiceList(List<ModelServiceRsp> serviceList) {
        this.serviceList = serviceList;
        return this;
    }

    public String getDomainId() {
        return domainId;
    }

    public RouterStrategyBaseInfo setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public RouterStrategyBaseInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public RouterStrategyBaseInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getCreatedByUserName() {
        return createdByUserName;
    }

    public RouterStrategyBaseInfo setCreatedByUserName(String createdByUserName) {
        this.createdByUserName = createdByUserName;
        return this;
    }

    public Long getCreatedDate() {
        return createdDate;
    }

    public RouterStrategyBaseInfo setCreatedDate(Long createdDate) {
        this.createdDate = createdDate;
        return this;
    }

    public Long getLastUpdatedDate() {
        return lastUpdatedDate;
    }

    public RouterStrategyBaseInfo setLastUpdatedDate(Long lastUpdatedDate) {
        this.lastUpdatedDate = lastUpdatedDate;
        return this;
    }

    public Integer getStrategyTimeout() {
        return strategyTimeout;
    }

    public RouterStrategyBaseInfo setStrategyTimeout(Integer strategyTimeout) {
        this.strategyTimeout = strategyTimeout;
        return this;
    }

    public Integer getStrategyRetryCount() {
        return strategyRetryCount;
    }

    public RouterStrategyBaseInfo setStrategyRetryCount(Integer strategyRetryCount) {
        this.strategyRetryCount = strategyRetryCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RouterStrategyBaseInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    strategyKey: ").append(toIndentedString(strategyKey)).append("\n");
        sb.append("    strategyName: ").append(toIndentedString(strategyName)).append("\n");
        sb.append("    strategyDescription: ").append(toIndentedString(strategyDescription)).append("\n");
        sb.append("    serviceList: ").append(toIndentedString(serviceList)).append("\n");
        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    createdByUserName: ").append(toIndentedString(createdByUserName)).append("\n");
        sb.append("    createdDate: ").append(toIndentedString(createdDate)).append("\n");
        sb.append("    lastUpdatedDate: ").append(toIndentedString(lastUpdatedDate)).append("\n");
        sb.append("    strategyTimeout: ").append(toIndentedString(strategyTimeout)).append("\n");
        sb.append("    strategyRetryCount: ").append(toIndentedString(strategyRetryCount)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        RouterStrategyBaseInfo routerStrategyBaseInfo = (RouterStrategyBaseInfo) obj;
        return Objects.equals(this.id, routerStrategyBaseInfo.id) && Objects.equals(this.strategyKey,
            routerStrategyBaseInfo.strategyKey) && Objects.equals(this.strategyName,
            routerStrategyBaseInfo.strategyName) && Objects.equals(this.strategyDescription,
            routerStrategyBaseInfo.strategyDescription) && Objects.equals(this.serviceList,
            routerStrategyBaseInfo.serviceList) && Objects.equals(this.domainId, routerStrategyBaseInfo.domainId)
            && Objects.equals(this.projectId, routerStrategyBaseInfo.projectId) && Objects.equals(this.workspaceId,
            routerStrategyBaseInfo.workspaceId) && Objects.equals(this.createdByUserName,
            routerStrategyBaseInfo.createdByUserName) && Objects.equals(this.createdDate,
            routerStrategyBaseInfo.createdDate) && Objects.equals(this.lastUpdatedDate,
            routerStrategyBaseInfo.lastUpdatedDate) && Objects.equals(this.strategyTimeout,
            routerStrategyBaseInfo.strategyTimeout) && Objects.equals(this.strategyRetryCount,
            routerStrategyBaseInfo.strategyRetryCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, strategyKey, strategyName, strategyDescription, serviceList, domainId, projectId,
            workspaceId, createdByUserName, createdDate, lastUpdatedDate, strategyTimeout, strategyRetryCount);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListAppRelationsQo: converted from multi query params
 */
@ApiModel(description = "ListAppRelationsQo: converted from multi query params")

@Validated

public class ListAppRelationsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1.0.0")
    @Length(max = 64)
    private String version = null;

    @JsonProperty("showlatest")
    @Schema(description = "是否展示最新版本", example = "true")
    private Boolean showlatest = null;

    @JsonProperty("resourceType")
    @Schema(description = "资源类型", example = "plugin")
    @Length(max = 20)
    private String resourceType = null;

    @JsonProperty("nestedCheck")
    @Schema(description = "是否嵌套检查", example = "false")
    private Boolean nestedCheck = false;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    public String getVersion() {
        return version;
    }

    public ListAppRelationsQo setVersion(String version) {
        this.version = version;
        return this;
    }

    public ListAppRelationsQo setShowlatest(Boolean showlatest) {
        this.showlatest = showlatest;
        return this;
    }

    public Boolean isShowlatest() {
        return showlatest;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ListAppRelationsQo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public ListAppRelationsQo setNestedCheck(Boolean nestedCheck) {
        this.nestedCheck = nestedCheck;
        return this;
    }

    public Boolean isNestedCheck() {
        return nestedCheck;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListAppRelationsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListAppRelationsQo {\n");

        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    showlatest: ").append(toIndentedString(showlatest)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    nestedCheck: ").append(toIndentedString(nestedCheck)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ListAppRelationsQo listAppRelationsQo = (ListAppRelationsQo) o;
        return Objects.equals(this.version, listAppRelationsQo.version) && Objects.equals(this.showlatest,
            listAppRelationsQo.showlatest) && Objects.equals(this.resourceType, listAppRelationsQo.resourceType)
            && Objects.equals(this.nestedCheck, listAppRelationsQo.nestedCheck) && Objects.equals(this.workspaceId,
            listAppRelationsQo.workspaceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(version, showlatest, resourceType, nestedCheck, workspaceId);
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

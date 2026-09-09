/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 修改工作空间请求体。
 */
@ApiModel(description = "修改工作空间请求体。")

@Validated

public class UpdateWorkspaceReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "工作空间ID", example = "ws001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "工作空间名称", example = "我的工作空间", required = true)
    @Pattern(
        regexp = "^[\\\\u4e00-\\\\u9fa5a-zA-Z0-9_\\\\-（）()！!](?:[\\\\u4e00-\\\\u9fa5a-zA-Z0-9_\\\\-（）()！! ]*[\\\\u4e00-\\\\u9fa5a-zA-Z0-9_\\\\-（）()！!])?$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String name = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon.png")
    private String icon = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "用于团队协作的工作空间")
    @Length(max = 256)
    private String description = null;

    @JsonProperty("externalMappingInfo")
    @Schema(description = "外部映射信息", example = "{}")
    @Valid
    private ExternalMappingInfo externalMappingInfo = null;

    public String getId() {
        return id;
    }

    public UpdateWorkspaceReq setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public UpdateWorkspaceReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public UpdateWorkspaceReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public UpdateWorkspaceReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public ExternalMappingInfo getExternalMappingInfo() {
        return externalMappingInfo;
    }

    public UpdateWorkspaceReq setExternalMappingInfo(ExternalMappingInfo externalMappingInfo) {
        this.externalMappingInfo = externalMappingInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateWorkspaceReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    externalMappingInfo: ").append(toIndentedString(externalMappingInfo)).append("\n");
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
        UpdateWorkspaceReq updateWorkspaceReq = (UpdateWorkspaceReq) o;
        return Objects.equals(this.id, updateWorkspaceReq.id) && Objects.equals(this.name, updateWorkspaceReq.name)
            && Objects.equals(this.icon, updateWorkspaceReq.icon) && Objects.equals(this.description,
            updateWorkspaceReq.description) && Objects.equals(this.externalMappingInfo,
            updateWorkspaceReq.externalMappingInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, icon, description, externalMappingInfo);
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

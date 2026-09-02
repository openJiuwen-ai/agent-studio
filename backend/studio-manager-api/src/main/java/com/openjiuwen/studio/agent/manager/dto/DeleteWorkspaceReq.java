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
 * 删除工作空间请求体。
 */
@ApiModel(description = "删除工作空间请求体。")

@Validated

public class DeleteWorkspaceReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("externalMappingInfo")
    @Schema(description = "外部mapping信息", example = "{}")
    @Valid
    private ExternalMappingInfo externalMappingInfo = null;

    public String getId() {
        return id;
    }

    public DeleteWorkspaceReq setId(String id) {
        this.id = id;
        return this;
    }

    public ExternalMappingInfo getExternalMappingInfo() {
        return externalMappingInfo;
    }

    public DeleteWorkspaceReq setExternalMappingInfo(ExternalMappingInfo externalMappingInfo) {
        this.externalMappingInfo = externalMappingInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeleteWorkspaceReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        DeleteWorkspaceReq deleteWorkspaceReq = (DeleteWorkspaceReq) o;
        return Objects.equals(this.id, deleteWorkspaceReq.id) && Objects.equals(this.externalMappingInfo,
            deleteWorkspaceReq.externalMappingInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, externalMappingInfo);
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

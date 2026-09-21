/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 和外部空间映射信息。
 */
@ApiModel(description = "和外部空间映射信息。")

@Validated

public class ExternalMappingInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspaceId")
    @Schema(description = "工作空间ID", example = "ws-001")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("mappingId")
    @Schema(description = "映射ID", example = "map-001")
    @Length(max = 128)
    private String mappingId = null;

    @JsonProperty("extensionContent")
    @Schema(description = "扩展内容列表", example = "[{\"key\":\"value\"}]")
    @Valid
    @Size()
    private List<Extension> extensionContent = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "external")
    private String source = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ExternalMappingInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getMappingId() {
        return mappingId;
    }

    public ExternalMappingInfo setMappingId(String mappingId) {
        this.mappingId = mappingId;
        return this;
    }

    public List<Extension> getExtensionContent() {
        return extensionContent;
    }

    public ExternalMappingInfo setExtensionContent(List<Extension> extensionContent) {
        this.extensionContent = extensionContent;
        return this;
    }

    public String getSource() {
        return source;
    }

    public ExternalMappingInfo setSource(String source) {
        this.source = source;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExternalMappingInfo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    mappingId: ").append(toIndentedString(mappingId)).append("\n");
        sb.append("    extensionContent: ").append(toIndentedString(extensionContent)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
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
        ExternalMappingInfo externalMappingInfo = (ExternalMappingInfo) o;
        return Objects.equals(this.workspaceId, externalMappingInfo.workspaceId) && Objects.equals(this.mappingId,
            externalMappingInfo.mappingId) && Objects.equals(this.extensionContent,
            externalMappingInfo.extensionContent) && Objects.equals(this.source, externalMappingInfo.source);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, mappingId, extensionContent, source);
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

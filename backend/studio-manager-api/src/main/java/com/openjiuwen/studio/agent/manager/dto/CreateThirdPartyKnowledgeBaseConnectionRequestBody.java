/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import com.openjiuwen.studio.agent.common.annotation.ValidKnowledgeBaseName;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * CreateThirdPartyKnowledgeBaseConnectionRequestBody
 */

@Validated

public class CreateThirdPartyKnowledgeBaseConnectionRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "知识库名称", example = "my-knowledge-base")
    @ValidKnowledgeBaseName
    @Length(max = 50)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "知识库描述")
    @Length(max = 100)
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "data:image/png;base64,iVBORw0KGgo=")
    @Length(max = 1024000)
    private String icon = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "connector-001")
    private String connectorId = null;

    @JsonProperty("params")
    @Schema(description = "连接参数列表", example = "[]")
    @Valid
    @Size(max = 10)
    private List<ConnectionParamInfo> params = null;

    public String getName() {
        return name;
    }

    public CreateThirdPartyKnowledgeBaseConnectionRequestBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public CreateThirdPartyKnowledgeBaseConnectionRequestBody setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public CreateThirdPartyKnowledgeBaseConnectionRequestBody setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public CreateThirdPartyKnowledgeBaseConnectionRequestBody setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public List<ConnectionParamInfo> getParams() {
        return params;
    }

    public CreateThirdPartyKnowledgeBaseConnectionRequestBody setParams(List<ConnectionParamInfo> params) {
        this.params = params;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateThirdPartyKnowledgeBaseConnectionRequestBody {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
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
        CreateThirdPartyKnowledgeBaseConnectionRequestBody createThirdPartyKnowledgeBaseConnectionRequestBody
            = (CreateThirdPartyKnowledgeBaseConnectionRequestBody) o;
        return Objects.equals(this.name, createThirdPartyKnowledgeBaseConnectionRequestBody.name) && Objects.equals(
            this.description, createThirdPartyKnowledgeBaseConnectionRequestBody.description) && Objects.equals(
            this.icon, createThirdPartyKnowledgeBaseConnectionRequestBody.icon) && Objects.equals(this.connectorId,
            createThirdPartyKnowledgeBaseConnectionRequestBody.connectorId) && Objects.equals(this.params,
            createThirdPartyKnowledgeBaseConnectionRequestBody.params);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, icon, connectorId, params);
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

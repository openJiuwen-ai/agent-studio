/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 第三方知识库连接测试请求体
 */
@ApiModel(description = "第三方知识库连接测试请求体")

@Validated

public class TestDefaultKnowledgeBaseConnectionRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(max = 50)
    private String connectorId = null;

    @JsonProperty("params")
    @Schema(description = "参数", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 10)
    private List<ConnectionParamInfo> params = new ArrayList<ConnectionParamInfo>();

    public String getConnectorId() {
        return connectorId;
    }

    public TestDefaultKnowledgeBaseConnectionRequestBody setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public List<ConnectionParamInfo> getParams() {
        return params;
    }

    public TestDefaultKnowledgeBaseConnectionRequestBody setParams(List<ConnectionParamInfo> params) {
        this.params = params;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TestDefaultKnowledgeBaseConnectionRequestBody {\n");

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
        TestDefaultKnowledgeBaseConnectionRequestBody testDefaultKnowledgeBaseConnectionRequestBody
            = (TestDefaultKnowledgeBaseConnectionRequestBody) o;
        return Objects.equals(this.connectorId, testDefaultKnowledgeBaseConnectionRequestBody.connectorId)
            && Objects.equals(this.params, testDefaultKnowledgeBaseConnectionRequestBody.params);
    }

    @Override
    public int hashCode() {
        return Objects.hash(connectorId, params);
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

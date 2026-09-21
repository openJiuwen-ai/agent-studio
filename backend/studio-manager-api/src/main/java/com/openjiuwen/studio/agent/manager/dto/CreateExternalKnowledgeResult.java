/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建第三方知识库的结果
 */
@ApiModel(description = "创建第三方知识库的结果")

@Validated

public class CreateExternalKnowledgeResult implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_id")
    @Schema(description = "知识库ID", example = "kb-001")
    @Length(min = 1, max = 100)
    private String knowledgeBaseId = null;

    @JsonProperty("knowledge_base_external_id")
    @Schema(description = "外部知识库ID", example = "ext-kb-001")
    @Length(max = 100)
    private String knowledgeBaseExternalId = null;

    @JsonProperty("result")
    @Schema(description = "创建结果", example = "true")
    private Boolean result = null;

    @JsonProperty("error_msg")
    @Schema(description = "错误信息", example = "创建成功")
    @Length(max = 1000)
    private String errorMsg = null;

    public String getKnowledgeBaseId() {
        return knowledgeBaseId;
    }

    public CreateExternalKnowledgeResult setKnowledgeBaseId(String knowledgeBaseId) {
        this.knowledgeBaseId = knowledgeBaseId;
        return this;
    }

    public String getKnowledgeBaseExternalId() {
        return knowledgeBaseExternalId;
    }

    public CreateExternalKnowledgeResult setKnowledgeBaseExternalId(String knowledgeBaseExternalId) {
        this.knowledgeBaseExternalId = knowledgeBaseExternalId;
        return this;
    }

    public CreateExternalKnowledgeResult setResult(Boolean result) {
        this.result = result;
        return this;
    }

    public Boolean isResult() {
        return result;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public CreateExternalKnowledgeResult setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateExternalKnowledgeResult {\n");

        sb.append("    knowledgeBaseId: ").append(toIndentedString(knowledgeBaseId)).append("\n");
        sb.append("    knowledgeBaseExternalId: ").append(toIndentedString(knowledgeBaseExternalId)).append("\n");
        sb.append("    result: ").append(toIndentedString(result)).append("\n");
        sb.append("    errorMsg: ").append(toIndentedString(errorMsg)).append("\n");
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
        CreateExternalKnowledgeResult createExternalKnowledgeResult = (CreateExternalKnowledgeResult) o;
        return Objects.equals(this.knowledgeBaseId, createExternalKnowledgeResult.knowledgeBaseId) && Objects.equals(
            this.knowledgeBaseExternalId, createExternalKnowledgeResult.knowledgeBaseExternalId) && Objects.equals(
            this.result, createExternalKnowledgeResult.result) && Objects.equals(this.errorMsg,
            createExternalKnowledgeResult.errorMsg);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseId, knowledgeBaseExternalId, result, errorMsg);
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

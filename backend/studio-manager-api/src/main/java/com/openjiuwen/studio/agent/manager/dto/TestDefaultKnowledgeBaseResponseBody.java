/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 默认知识库测试连接请求体
 */
@ApiModel(description = "默认知识库测试连接请求体")

@Validated

public class TestDefaultKnowledgeBaseResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("result")
    @Schema(description = "结果", example = "true")
    private Boolean result = null;

    public TestDefaultKnowledgeBaseResponseBody setResult(Boolean result) {
        this.result = result;
        return this;
    }

    public Boolean isResult() {
        return result;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TestDefaultKnowledgeBaseResponseBody {\n");

        sb.append("    result: ").append(toIndentedString(result)).append("\n");
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
        TestDefaultKnowledgeBaseResponseBody testDefaultKnowledgeBaseResponseBody
            = (TestDefaultKnowledgeBaseResponseBody) o;
        return Objects.equals(this.result, testDefaultKnowledgeBaseResponseBody.result);
    }

    @Override
    public int hashCode() {
        return Objects.hash(result);
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

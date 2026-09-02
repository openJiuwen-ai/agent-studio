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
 * 创建知识库OBS配置返回体。
 */
@ApiModel(description = "创建知识库OBS配置返回体。")

@Validated

public class CreateKnowledgeBaseObsConfigResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    public String getId() {
        return id;
    }

    public CreateKnowledgeBaseObsConfigResp setId(String id) {
        this.id = id;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeBaseObsConfigResp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        CreateKnowledgeBaseObsConfigResp createKnowledgeBaseObsConfigResp = (CreateKnowledgeBaseObsConfigResp) o;
        return Objects.equals(this.id, createKnowledgeBaseObsConfigResp.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
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

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
 * 知识库OBS配置详情。
 */
@ApiModel(description = "知识库OBS配置详情。")

@Validated

public class KnowledgeBaseObsConfigResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    @JsonProperty("obs_bucket_name")
    @Schema(description = "OBS桶名称", example = "示例名称")
    private String obsBucketName = null;

    @JsonProperty("obs_input_directory")
    @Schema(description = "输入", example = "示例字符串")
    private String obsInputDirectory = null;

    public String getId() {
        return id;
    }

    public KnowledgeBaseObsConfigResp setId(String id) {
        this.id = id;
        return this;
    }

    public String getObsBucketName() {
        return obsBucketName;
    }

    public KnowledgeBaseObsConfigResp setObsBucketName(String obsBucketName) {
        this.obsBucketName = obsBucketName;
        return this;
    }

    public String getObsInputDirectory() {
        return obsInputDirectory;
    }

    public KnowledgeBaseObsConfigResp setObsInputDirectory(String obsInputDirectory) {
        this.obsInputDirectory = obsInputDirectory;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseObsConfigResp {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    obsBucketName: ").append(toIndentedString(obsBucketName)).append("\n");
        sb.append("    obsInputDirectory: ").append(toIndentedString(obsInputDirectory)).append("\n");
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
        KnowledgeBaseObsConfigResp knowledgeBaseObsConfigResp = (KnowledgeBaseObsConfigResp) o;
        return Objects.equals(this.id, knowledgeBaseObsConfigResp.id) && Objects.equals(this.obsBucketName,
            knowledgeBaseObsConfigResp.obsBucketName) && Objects.equals(this.obsInputDirectory,
            knowledgeBaseObsConfigResp.obsInputDirectory);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, obsBucketName, obsInputDirectory);
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

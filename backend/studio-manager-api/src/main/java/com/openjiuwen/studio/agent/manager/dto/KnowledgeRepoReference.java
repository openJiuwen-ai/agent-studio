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
 * 关联知识库对象。
 */
@ApiModel(description = "关联知识库对象。")

@Validated

public class KnowledgeRepoReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_repo_id")
    @Schema(description = "知识库ID", example = "kr001")
    private String knowledgeRepoId = null;

    @JsonProperty("knowledge_repo_name")
    @Schema(description = "知识库名称", example = "产品知识库")
    private String knowledgeRepoName = null;

    @JsonProperty("knowledge_repo_icon")
    @Schema(description = "知识库图标", example = "icon.png")
    private String knowledgeRepoIcon = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    @Length(min = 1, max = 16)
    private String status = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "产品相关知识库")
    @Length(min = 1, max = 100)
    private String desc = null;

    public String getKnowledgeRepoId() {
        return knowledgeRepoId;
    }

    public KnowledgeRepoReference setKnowledgeRepoId(String knowledgeRepoId) {
        this.knowledgeRepoId = knowledgeRepoId;
        return this;
    }

    public String getKnowledgeRepoName() {
        return knowledgeRepoName;
    }

    public KnowledgeRepoReference setKnowledgeRepoName(String knowledgeRepoName) {
        this.knowledgeRepoName = knowledgeRepoName;
        return this;
    }

    public String getKnowledgeRepoIcon() {
        return knowledgeRepoIcon;
    }

    public KnowledgeRepoReference setKnowledgeRepoIcon(String knowledgeRepoIcon) {
        this.knowledgeRepoIcon = knowledgeRepoIcon;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public KnowledgeRepoReference setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public KnowledgeRepoReference setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeRepoReference {\n");

        sb.append("    knowledgeRepoId: ").append(toIndentedString(knowledgeRepoId)).append("\n");
        sb.append("    knowledgeRepoName: ").append(toIndentedString(knowledgeRepoName)).append("\n");
        sb.append("    knowledgeRepoIcon: ").append(toIndentedString(knowledgeRepoIcon)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
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
        KnowledgeRepoReference knowledgeRepoReference = (KnowledgeRepoReference) o;
        return Objects.equals(this.knowledgeRepoId, knowledgeRepoReference.knowledgeRepoId) && Objects.equals(
            this.knowledgeRepoName, knowledgeRepoReference.knowledgeRepoName) && Objects.equals(this.knowledgeRepoIcon,
            knowledgeRepoReference.knowledgeRepoIcon) && Objects.equals(this.status, knowledgeRepoReference.status)
            && Objects.equals(this.desc, knowledgeRepoReference.desc);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeRepoId, knowledgeRepoName, knowledgeRepoIcon, status, desc);
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

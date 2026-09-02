/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 创建知识库分层规则请求体
 */
@ApiModel(description = "创建知识库分层规则请求体")

@Validated

public class CreateKnowledgeSegmentRuleRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("rule_regexs")
    @Schema(description = "ruleregexs", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 10)
    private List<@Length(max = 1024) String> ruleRegexs = new ArrayList<String>();

    @JsonProperty("repo_id")
    @Schema(description = "ID", example = "example-id-123")
    @Length(min = 1, max = 100)
    private String repoId = null;

    public List<String> getRuleRegexs() {
        return ruleRegexs;
    }

    public CreateKnowledgeSegmentRuleRequestBody setRuleRegexs(List<String> ruleRegexs) {
        this.ruleRegexs = ruleRegexs;
        return this;
    }

    public String getRepoId() {
        return repoId;
    }

    public CreateKnowledgeSegmentRuleRequestBody setRepoId(String repoId) {
        this.repoId = repoId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeSegmentRuleRequestBody {\n");

        sb.append("    ruleRegexs: ").append(toIndentedString(ruleRegexs)).append("\n");
        sb.append("    repoId: ").append(toIndentedString(repoId)).append("\n");
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
        CreateKnowledgeSegmentRuleRequestBody createKnowledgeSegmentRuleRequestBody
            = (CreateKnowledgeSegmentRuleRequestBody) o;
        return Objects.equals(this.ruleRegexs, createKnowledgeSegmentRuleRequestBody.ruleRegexs) && Objects.equals(
            this.repoId, createKnowledgeSegmentRuleRequestBody.repoId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ruleRegexs, repoId);
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

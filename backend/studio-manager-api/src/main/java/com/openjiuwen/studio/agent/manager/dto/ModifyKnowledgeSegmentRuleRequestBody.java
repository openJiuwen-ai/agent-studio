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
 * 修改知识库分层规则请求体
 */
@ApiModel(description = "修改知识库分层规则请求体")

@Validated

public class ModifyKnowledgeSegmentRuleRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("rule_regexs")
    @Schema(description = "ruleregexs", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 10)
    private List<@Length(max = 1024) String> ruleRegexs = new ArrayList<String>();

    public List<String> getRuleRegexs() {
        return ruleRegexs;
    }

    public ModifyKnowledgeSegmentRuleRequestBody setRuleRegexs(List<String> ruleRegexs) {
        this.ruleRegexs = ruleRegexs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyKnowledgeSegmentRuleRequestBody {\n");

        sb.append("    ruleRegexs: ").append(toIndentedString(ruleRegexs)).append("\n");
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
        ModifyKnowledgeSegmentRuleRequestBody modifyKnowledgeSegmentRuleRequestBody
            = (ModifyKnowledgeSegmentRuleRequestBody) o;
        return Objects.equals(this.ruleRegexs, modifyKnowledgeSegmentRuleRequestBody.ruleRegexs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ruleRegexs);
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

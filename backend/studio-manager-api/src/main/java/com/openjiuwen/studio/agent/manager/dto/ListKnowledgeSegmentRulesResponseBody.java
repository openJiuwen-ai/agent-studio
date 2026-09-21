/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 查询知识库分层规则列表响应体
 */
@ApiModel(description = "查询知识库分层规则列表响应体")

@Validated

public class ListKnowledgeSegmentRulesResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    @Range(min = 0L, max = 65535L)
    private Integer count = null;

    @JsonProperty("rule_list")
    @Schema(description = "rule列表", example = "[]")
    @Valid
    @Size(max = 65535)
    private List<KnowledgeSegmentRule> ruleList = null;

    public Integer getCount() {
        return count;
    }

    public ListKnowledgeSegmentRulesResponseBody setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<KnowledgeSegmentRule> getRuleList() {
        return ruleList;
    }

    public ListKnowledgeSegmentRulesResponseBody setRuleList(List<KnowledgeSegmentRule> ruleList) {
        this.ruleList = ruleList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeSegmentRulesResponseBody {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    ruleList: ").append(toIndentedString(ruleList)).append("\n");
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
        ListKnowledgeSegmentRulesResponseBody listKnowledgeSegmentRulesResponseBody
            = (ListKnowledgeSegmentRulesResponseBody) o;
        return Objects.equals(this.count, listKnowledgeSegmentRulesResponseBody.count) && Objects.equals(this.ruleList,
            listKnowledgeSegmentRulesResponseBody.ruleList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, ruleList);
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

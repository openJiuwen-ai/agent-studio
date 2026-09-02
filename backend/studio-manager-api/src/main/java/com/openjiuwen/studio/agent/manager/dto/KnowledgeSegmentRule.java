/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 知识库分层规则
 */
@ApiModel(description = "知识库分层规则")

@Validated

public class KnowledgeSegmentRule implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "rule_001")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("rule_regexs")
    @Schema(description = "规则正则表达式列表", example = "[\".*\\\\.pdf\",\".*\\\\.docx\"]")
    @Valid
    @Size(max = 65535)
    private List<@Length(max = 1024) String> ruleRegexs = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project_001")
    @Length(min = 1, max = 64)
    private String projectId = null;

    @JsonProperty("creator")
    @Schema(description = "创建者名称", example = "张三")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1714521600000")
    @Range(min = 0L, max = 253402214400000L)
    private Long createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1714608000000")
    @Range(min = 0L, max = 253402214400000L)
    private Long updateTime = null;

    public String getId() {
        return id;
    }

    public KnowledgeSegmentRule setId(String id) {
        this.id = id;
        return this;
    }

    public List<String> getRuleRegexs() {
        return ruleRegexs;
    }

    public KnowledgeSegmentRule setRuleRegexs(List<String> ruleRegexs) {
        this.ruleRegexs = ruleRegexs;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public KnowledgeSegmentRule setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public KnowledgeSegmentRule setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public KnowledgeSegmentRule setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public KnowledgeSegmentRule setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public KnowledgeSegmentRule setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeSegmentRule {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    ruleRegexs: ").append(toIndentedString(ruleRegexs)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
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
        KnowledgeSegmentRule knowledgeSegmentRule = (KnowledgeSegmentRule) o;
        return Objects.equals(this.id, knowledgeSegmentRule.id) && Objects.equals(this.ruleRegexs,
            knowledgeSegmentRule.ruleRegexs) && Objects.equals(this.projectId, knowledgeSegmentRule.projectId)
            && Objects.equals(this.creator, knowledgeSegmentRule.creator) && Objects.equals(this.creatorId,
            knowledgeSegmentRule.creatorId) && Objects.equals(this.createTime, knowledgeSegmentRule.createTime)
            && Objects.equals(this.updateTime, knowledgeSegmentRule.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, ruleRegexs, projectId, creator, creatorId, createTime, updateTime);
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

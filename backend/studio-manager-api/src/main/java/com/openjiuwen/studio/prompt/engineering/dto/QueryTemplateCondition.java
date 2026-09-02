/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
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
 * QueryTemplateCondition
 */

@Validated
public class QueryTemplateCondition implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("template_id")
    @Schema(description = "模板ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String templateId = null;

    @JsonProperty("template_name")
    @Schema(description = "模板名称", example = "示例名称")
    private String templateName = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容")
    private String content = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("tag_list")
    @Schema(description = "标签列表", example = "")
    @Valid
    @Size(max = 500)
    private List<@Length() String> tagList = null;

    @JsonProperty("industry_list")
    @Schema(description = "行业列表", example = "")
    @Valid
    @Size(max = 500)
    private List<@Length() String> industryList = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "PLAYGROUND")
    private String source = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 100000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "50")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 50;

    public String getTemplateId() {
        return templateId;
    }

    public QueryTemplateCondition setTemplateId(String templateId) {
        this.templateId = templateId;
        return this;
    }

    public String getTemplateName() {
        return templateName;
    }

    public QueryTemplateCondition setTemplateName(String templateName) {
        this.templateName = templateName;
        return this;
    }

    public String getContent() {
        return content;
    }

    public QueryTemplateCondition setContent(String content) {
        this.content = content;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public QueryTemplateCondition setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<String> getTagList() {
        return tagList;
    }

    public QueryTemplateCondition setTagList(List<String> tagList) {
        this.tagList = tagList;
        return this;
    }

    public List<String> getIndustryList() {
        return industryList;
    }

    public QueryTemplateCondition setIndustryList(List<String> industryList) {
        this.industryList = industryList;
        return this;
    }

    public String getSource() {
        return source;
    }

    public QueryTemplateCondition setSource(String source) {
        this.source = source;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public QueryTemplateCondition setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public QueryTemplateCondition setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryTemplateCondition {\n");
        sb.append("    templateId: ").append(toIndentedString(templateId)).append("\n");
        sb.append("    templateName: ").append(toIndentedString(templateName)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    tagList: ").append(toIndentedString(tagList)).append("\n");
        sb.append("    industryList: ").append(toIndentedString(industryList)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
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
        QueryTemplateCondition queryTemplateCondition = (QueryTemplateCondition) o;
        return Objects.equals(this.templateId, queryTemplateCondition.templateId) && Objects.equals(this.templateName,
            queryTemplateCondition.templateName) && Objects.equals(this.content, queryTemplateCondition.content)
            && Objects.equals(this.description, queryTemplateCondition.description) && Objects.equals(this.tagList,
            queryTemplateCondition.tagList) && Objects.equals(this.industryList, queryTemplateCondition.industryList)
            && Objects.equals(this.source, queryTemplateCondition.source) && Objects.equals(this.offset,
            queryTemplateCondition.offset) && Objects.equals(this.limit, queryTemplateCondition.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(templateId, templateName, content, description, tagList, industryList, source, offset,
            limit);
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

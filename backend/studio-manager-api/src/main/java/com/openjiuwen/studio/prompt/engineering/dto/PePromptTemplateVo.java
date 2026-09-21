/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * PePromptTemplateVo
 */

@Validated
public class PePromptTemplateVo implements Serializable {

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

    @JsonProperty("variables")
    @Schema(description = "变量", example = "[{\"name\":\"var1\",\"type\":\"string\",\"value\":\"val1\"}]")
    private String variables = null;

    @JsonProperty("tag_list")
    @Schema(description = "标签列表", example = "")
    @Valid
    @Size(max = 500)
    private List<TagVo> tagList = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("created_on")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000Z")
    private String createdOn = null;

    @JsonProperty("updated_on")
    @Schema(description = "更新时间", example = "2024-01-01T00:00:00.000Z")
    private String updatedOn = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("industry")
    @Schema(description = "行业信息", example = "")
    @Valid
    private IndustryVo industry = null;

    @JsonProperty("pt_type")
    @Schema(description = "提示词类型", example = "text")
    @Pattern(regexp = "multi|text")
    private String ptType = null;

    @JsonProperty("is_share")
    @Schema(description = "是否共享", example = "1")
    private Integer isShare = null;

    public String getTemplateId() {
        return templateId;
    }

    public PePromptTemplateVo setTemplateId(String templateId) {
        this.templateId = templateId;
        return this;
    }

    public String getTemplateName() {
        return templateName;
    }

    public PePromptTemplateVo setTemplateName(String templateName) {
        this.templateName = templateName;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PePromptTemplateVo setContent(String content) {
        this.content = content;
        return this;
    }

    public String getVariables() {
        return variables;
    }

    public PePromptTemplateVo setVariables(String variables) {
        this.variables = variables;
        return this;
    }

    public List<TagVo> getTagList() {
        return tagList;
    }

    public PePromptTemplateVo setTagList(List<TagVo> tagList) {
        this.tagList = tagList;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PePromptTemplateVo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatedOn() {
        return createdOn;
    }

    public PePromptTemplateVo setCreatedOn(String createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public String getUpdatedOn() {
        return updatedOn;
    }

    public PePromptTemplateVo setUpdatedOn(String updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public PePromptTemplateVo setDescription(String description) {
        this.description = description;
        return this;
    }

    public IndustryVo getIndustry() {
        return industry;
    }

    public PePromptTemplateVo setIndustry(IndustryVo industry) {
        this.industry = industry;
        return this;
    }

    public String getPtType() {
        return ptType;
    }

    public PePromptTemplateVo setPtType(String ptType) {
        this.ptType = ptType;
        return this;
    }

    public Integer getIsShare() {
        return isShare;
    }

    public PePromptTemplateVo setIsShare(Integer isShare) {
        this.isShare = isShare;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptTemplateVo {\n");
        sb.append("    templateId: ").append(toIndentedString(templateId)).append("\n");
        sb.append("    templateName: ").append(toIndentedString(templateName)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    tagList: ").append(toIndentedString(tagList)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    industry: ").append(toIndentedString(industry)).append("\n");
        sb.append("    ptType: ").append(toIndentedString(ptType)).append("\n");
        sb.append("    isShare: ").append(toIndentedString(isShare)).append("\n");
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
        PePromptTemplateVo pePromptTemplateVo = (PePromptTemplateVo) o;
        return Objects.equals(this.templateId, pePromptTemplateVo.templateId) && Objects.equals(this.templateName,
            pePromptTemplateVo.templateName) && Objects.equals(this.content, pePromptTemplateVo.content)
            && Objects.equals(this.variables, pePromptTemplateVo.variables) && Objects.equals(this.tagList,
            pePromptTemplateVo.tagList) && Objects.equals(this.creator, pePromptTemplateVo.creator) && Objects.equals(
            this.createdOn, pePromptTemplateVo.createdOn) && Objects.equals(this.updatedOn,
            pePromptTemplateVo.updatedOn) && Objects.equals(this.description, pePromptTemplateVo.description)
            && Objects.equals(this.industry, pePromptTemplateVo.industry) && Objects.equals(this.ptType,
            pePromptTemplateVo.ptType) && Objects.equals(this.isShare, pePromptTemplateVo.isShare);
    }

    @Override
    public int hashCode() {
        return Objects.hash(templateId, templateName, content, variables, tagList, creator, createdOn, updatedOn,
            description, industry, ptType, isShare);
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

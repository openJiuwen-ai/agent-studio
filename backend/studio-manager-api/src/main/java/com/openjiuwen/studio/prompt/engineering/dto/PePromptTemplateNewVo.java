/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 创建模板请求体
 */
@ApiModel(description = "创建模板请求体")

@Validated
public class PePromptTemplateNewVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-()（）]{0,32}[\\u4e00-\\u9fa5a-zA-Z0-9()（）]$")
    @NotBlank
    private String name = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容", required = true)
    @NotBlank
    @Length(min = 1, max = 10000)
    private String content = null;

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
    @Length(max = 255)
    private String description = null;

    @JsonProperty("industry_id")
    @Schema(description = "行业ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String industryId = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "PLAYGROUND", required = true)
    @Pattern(regexp = "PLAYGROUND|EXPERIMENT|CANDIDATE|HORIZONTAL|NO_SOURCE|PRESET")
    @NotBlank
    private String source = null;

    @JsonProperty("variables")
    @Schema(description = "变量", example = "[{\"name\":\"var1\",\"type\":\"string\",\"value\":\"val1\"}]")
    private String variables = null;

    @JsonProperty("pt_type")
    @Schema(description = "提示词类型", example = "text")
    @Pattern(regexp = "multi|text")
    private String ptType = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "")
    @Valid
    private List<@Length() String> tags = null;

    public String getId() {
        return id;
    }

    public PePromptTemplateNewVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public PePromptTemplateNewVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PePromptTemplateNewVo setContent(String content) {
        this.content = content;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PePromptTemplateNewVo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatedOn() {
        return createdOn;
    }

    public PePromptTemplateNewVo setCreatedOn(String createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public String getUpdatedOn() {
        return updatedOn;
    }

    public PePromptTemplateNewVo setUpdatedOn(String updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public PePromptTemplateNewVo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIndustryId() {
        return industryId;
    }

    public PePromptTemplateNewVo setIndustryId(String industryId) {
        this.industryId = industryId;
        return this;
    }

    public String getSource() {
        return source;
    }

    public PePromptTemplateNewVo setSource(String source) {
        this.source = source;
        return this;
    }

    public String getVariables() {
        return variables;
    }

    public PePromptTemplateNewVo setVariables(String variables) {
        this.variables = variables;
        return this;
    }

    public String getPtType() {
        return ptType;
    }

    public PePromptTemplateNewVo setPtType(String ptType) {
        this.ptType = ptType;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public PePromptTemplateNewVo setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptTemplateNewVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    industryId: ").append(toIndentedString(industryId)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    ptType: ").append(toIndentedString(ptType)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
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
        PePromptTemplateNewVo pePromptTemplateNewVo = (PePromptTemplateNewVo) o;
        return Objects.equals(this.id, pePromptTemplateNewVo.id) && Objects.equals(this.name,
            pePromptTemplateNewVo.name) && Objects.equals(this.content, pePromptTemplateNewVo.content)
            && Objects.equals(this.creator, pePromptTemplateNewVo.creator) && Objects.equals(this.createdOn,
            pePromptTemplateNewVo.createdOn) && Objects.equals(this.updatedOn, pePromptTemplateNewVo.updatedOn)
            && Objects.equals(this.description, pePromptTemplateNewVo.description) && Objects.equals(this.industryId,
            pePromptTemplateNewVo.industryId) && Objects.equals(this.source, pePromptTemplateNewVo.source)
            && Objects.equals(this.variables, pePromptTemplateNewVo.variables) && Objects.equals(this.ptType,
            pePromptTemplateNewVo.ptType) && Objects.equals(this.tags, pePromptTemplateNewVo.tags);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, content, creator, createdOn, updatedOn, description, industryId, source,
            variables, ptType, tags);
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

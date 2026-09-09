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
public class PePromptTemplateDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("prompt_id")
    @Schema(description = "提示词ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String promptId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,18}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    @NotBlank
    private String name = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容", required = true)
    @NotBlank
    @Length(max = 10000)
    private String content = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "PLAYGROUND", required = true)
    @Pattern(regexp = "PLAYGROUND|EXPERIMENT|CANDIDATE|HORIZONTAL|NO_SOURCE|PRESET")
    @NotBlank
    private String source = null;

    @JsonProperty("variables")
    @Schema(description = "变量", example = "[{\"name\":\"var1\",\"type\":\"string\",\"value\":\"val1\"}]")
    private String variables = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "")
    @Valid
    private List<@Length() String> tags = null;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String taskId = null;

    @JsonProperty("industry_id")
    @Schema(description = "行业ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String industryId = null;

    public String getId() {
        return id;
    }

    public PePromptTemplateDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getPromptId() {
        return promptId;
    }

    public PePromptTemplateDto setPromptId(String promptId) {
        this.promptId = promptId;
        return this;
    }

    public String getName() {
        return name;
    }

    public PePromptTemplateDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PePromptTemplateDto setContent(String content) {
        this.content = content;
        return this;
    }

    public String getSource() {
        return source;
    }

    public PePromptTemplateDto setSource(String source) {
        this.source = source;
        return this;
    }

    public String getVariables() {
        return variables;
    }

    public PePromptTemplateDto setVariables(String variables) {
        this.variables = variables;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public PePromptTemplateDto setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    public String getTaskId() {
        return taskId;
    }

    public PePromptTemplateDto setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getIndustryId() {
        return industryId;
    }

    public PePromptTemplateDto setIndustryId(String industryId) {
        this.industryId = industryId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptTemplateDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    promptId: ").append(toIndentedString(promptId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    industryId: ").append(toIndentedString(industryId)).append("\n");
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
        PePromptTemplateDto pePromptTemplateDto = (PePromptTemplateDto) o;
        return Objects.equals(this.id, pePromptTemplateDto.id) && Objects.equals(this.promptId,
            pePromptTemplateDto.promptId) && Objects.equals(this.name, pePromptTemplateDto.name) && Objects.equals(
            this.content, pePromptTemplateDto.content) && Objects.equals(this.source, pePromptTemplateDto.source)
            && Objects.equals(this.variables, pePromptTemplateDto.variables) && Objects.equals(this.tags,
            pePromptTemplateDto.tags) && Objects.equals(this.taskId, pePromptTemplateDto.taskId) && Objects.equals(
            this.industryId, pePromptTemplateDto.industryId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, promptId, name, content, source, variables, tags, taskId, industryId);
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

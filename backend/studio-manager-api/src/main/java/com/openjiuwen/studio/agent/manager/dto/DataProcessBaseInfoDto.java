/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 数据处理 服务信息
 */
@ApiModel(description = "数据处理 服务信息")

@Validated

public class DataProcessBaseInfoDto implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "服务ID", example = "dp-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "文本处理服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "text_processor")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "提供文本分割和清洗功能")
    private String description = null;

    @JsonProperty("type")
    @Schema(description = "服务类型", example = "tool")
    private String type = null;

    @JsonProperty("tools")
    @Schema(description = "工具信息", example = "{\"name\":\"text_splitter\"}")
    @Valid
    private McpDataProcessTool tools = null;

    public String getId() {
        return id;
    }

    public DataProcessBaseInfoDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public DataProcessBaseInfoDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public DataProcessBaseInfoDto setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public DataProcessBaseInfoDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getType() {
        return type;
    }

    public DataProcessBaseInfoDto setType(String type) {
        this.type = type;
        return this;
    }

    public McpDataProcessTool getTools() {
        return tools;
    }

    public DataProcessBaseInfoDto setTools(McpDataProcessTool tools) {
        this.tools = tools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DataProcessBaseInfoDto {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
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
        DataProcessBaseInfoDto dataProcessBaseInfoDto = (DataProcessBaseInfoDto) o;
        return Objects.equals(this.id, dataProcessBaseInfoDto.id) && Objects.equals(this.name,
            dataProcessBaseInfoDto.name) && Objects.equals(this.nameEn, dataProcessBaseInfoDto.nameEn)
            && Objects.equals(this.description, dataProcessBaseInfoDto.description) && Objects.equals(this.type,
            dataProcessBaseInfoDto.type) && Objects.equals(this.tools, dataProcessBaseInfoDto.tools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, type, tools);
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

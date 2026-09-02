/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * IndustryDto
 */

@Validated
public class IndustryDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,30}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "英文名称", example = "示例名称")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    public String getId() {
        return id;
    }

    public IndustryDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public IndustryDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public IndustryDto setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public IndustryDto setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class IndustryDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        IndustryDto industryDto = (IndustryDto) o;
        return Objects.equals(this.id, industryDto.id) && Objects.equals(this.name, industryDto.name) && Objects.equals(
            this.nameEn, industryDto.nameEn) && Objects.equals(this.description, industryDto.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description);
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

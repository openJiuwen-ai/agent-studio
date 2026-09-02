/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * IndustryVo
 */

@Validated
public class IndustryVo implements Serializable {

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

    @JsonProperty("library_type")
    @Schema(description = "库类型", example = "PUBLIC")
    private String libraryType = null;

    @JsonProperty("created_on")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000Z")
    private Date createdOn = null;

    @JsonProperty("updated_on")
    @Schema(description = "更新时间", example = "2024-01-01T00:00:00.000Z")
    private Date updatedOn = null;

    public String getId() {
        return id;
    }

    public IndustryVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public IndustryVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public IndustryVo setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public IndustryVo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getLibraryType() {
        return libraryType;
    }

    public IndustryVo setLibraryType(String libraryType) {
        this.libraryType = libraryType;
        return this;
    }

    public Date getCreatedOn() {
        return createdOn;
    }

    public IndustryVo setCreatedOn(Date createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public Date getUpdatedOn() {
        return updatedOn;
    }

    public IndustryVo setUpdatedOn(Date updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class IndustryVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    libraryType: ").append(toIndentedString(libraryType)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
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
        IndustryVo industryVo = (IndustryVo) o;
        return Objects.equals(this.id, industryVo.id) && Objects.equals(this.name, industryVo.name) && Objects.equals(
            this.nameEn, industryVo.nameEn) && Objects.equals(this.description, industryVo.description)
            && Objects.equals(this.libraryType, industryVo.libraryType) && Objects.equals(this.createdOn,
            industryVo.createdOn) && Objects.equals(this.updatedOn, industryVo.updatedOn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, libraryType, createdOn, updatedOn);
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

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 文件解析内容。
 */
@ApiModel(description = "文件解析内容。")

@Validated

public class ImportListInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "import_001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "导入文件1")
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "file")
    private String type = null;

    @JsonProperty("description")
    @Schema(description = "描述信息", example = "这是导入文件的描述")
    private String description = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "true")
    private Boolean status = false;

    @JsonProperty("prohibited")
    @Schema(description = "是否禁止", example = "false")
    private Boolean prohibited = false;

    @JsonProperty("import_description")
    @Schema(description = "导入描述", example = "从配置文件导入")
    private String importDescription = null;

    @JsonProperty("dependencies")
    @Schema(description = "依赖列表", example = "[{\"id\":\"dep_001\",\"name\":\"依赖1\"}]")
    @Valid
    @Size()
    private List<ImportListInfo> dependencies = null;

    public String getId() {
        return id;
    }

    public ImportListInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ImportListInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ImportListInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ImportListInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public ImportListInfo setStatus(Boolean status) {
        this.status = status;
        return this;
    }

    public Boolean isStatus() {
        return status;
    }

    public ImportListInfo setProhibited(Boolean prohibited) {
        this.prohibited = prohibited;
        return this;
    }

    public Boolean isProhibited() {
        return prohibited;
    }

    public String getImportDescription() {
        return importDescription;
    }

    public ImportListInfo setImportDescription(String importDescription) {
        this.importDescription = importDescription;
        return this;
    }

    public List<ImportListInfo> getDependencies() {
        return dependencies;
    }

    public ImportListInfo setDependencies(List<ImportListInfo> dependencies) {
        this.dependencies = dependencies;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ImportListInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    prohibited: ").append(toIndentedString(prohibited)).append("\n");
        sb.append("    importDescription: ").append(toIndentedString(importDescription)).append("\n");
        sb.append("    dependencies: ").append(toIndentedString(dependencies)).append("\n");
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
        ImportListInfo importListInfo = (ImportListInfo) o;
        return Objects.equals(this.id, importListInfo.id) && Objects.equals(this.name, importListInfo.name)
            && Objects.equals(this.type, importListInfo.type) && Objects.equals(this.description,
            importListInfo.description) && Objects.equals(this.status, importListInfo.status) && Objects.equals(
            this.prohibited, importListInfo.prohibited) && Objects.equals(this.importDescription,
            importListInfo.importDescription) && Objects.equals(this.dependencies, importListInfo.dependencies);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, description, status, prohibited, importDescription, dependencies);
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

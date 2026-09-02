/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 导入结果信息
 */
@ApiModel(description = "导入结果信息")

@Validated

public class ImportRes implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "res-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "知识库导入")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "knowledge_base")
    @Length(max = 64)
    private String type = null;

    @JsonProperty("version")
    @Schema(description = "版本", example = "1.0.0")
    @Length(max = 64)
    private String version = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "success")
    private String status = null;

    @JsonProperty("detail")
    @Schema(description = "详情", example = "导入成功")
    private String detail = null;

    @JsonProperty("suggestion")
    @Schema(description = "建议", example = "无")
    private String suggestion = null;

    @JsonProperty("config_display")
    @Schema(description = "是否展示配置", example = "true")
    private Boolean configDisplay = null;

    @JsonProperty("dependencies")
    @Schema(description = "依赖项列表", example = "[]")
    @Valid
    @Size()
    private List<ImportRes> dependencies = null;

    public String getId() {
        return id;
    }

    public ImportRes setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ImportRes setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ImportRes setType(String type) {
        this.type = type;
        return this;
    }

    public String getVersion() {
        return version;
    }

    public ImportRes setVersion(String version) {
        this.version = version;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ImportRes setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getDetail() {
        return detail;
    }

    public ImportRes setDetail(String detail) {
        this.detail = detail;
        return this;
    }

    public String getSuggestion() {
        return suggestion;
    }

    public ImportRes setSuggestion(String suggestion) {
        this.suggestion = suggestion;
        return this;
    }

    public ImportRes setConfigDisplay(Boolean configDisplay) {
        this.configDisplay = configDisplay;
        return this;
    }

    public Boolean isConfigDisplay() {
        return configDisplay;
    }

    public List<ImportRes> getDependencies() {
        return dependencies;
    }

    public ImportRes setDependencies(List<ImportRes> dependencies) {
        this.dependencies = dependencies;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ImportRes {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    detail: ").append(toIndentedString(detail)).append("\n");
        sb.append("    suggestion: ").append(toIndentedString(suggestion)).append("\n");
        sb.append("    configDisplay: ").append(toIndentedString(configDisplay)).append("\n");
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
        ImportRes importRes = (ImportRes) o;
        return Objects.equals(this.id, importRes.id) && Objects.equals(this.name, importRes.name) && Objects.equals(
            this.type, importRes.type) && Objects.equals(this.version, importRes.version) && Objects.equals(this.status,
            importRes.status) && Objects.equals(this.detail, importRes.detail) && Objects.equals(this.suggestion,
            importRes.suggestion) && Objects.equals(this.configDisplay, importRes.configDisplay) && Objects.equals(
            this.dependencies, importRes.dependencies);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, version, status, detail, suggestion, configDisplay, dependencies);
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

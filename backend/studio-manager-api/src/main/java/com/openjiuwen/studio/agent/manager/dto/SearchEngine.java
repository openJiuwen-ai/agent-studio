/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 搜索引擎配置。
 */
@ApiModel(description = "搜索引擎配置。")

@Validated

public class SearchEngine implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "搜索引擎ID", example = "engine_001")
    @Length(max = 1000)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "搜索引擎名称", example = "Google")
    @Length(max = 500)
    private String name = null;

    @JsonProperty("url")
    @Schema(description = "搜索引擎URL", example = "https://www.google.com")
    @Length(max = 1000)
    private String url = null;

    @JsonProperty("extension")
    @Schema(description = "搜索引擎扩展配置", example = "search_ext")
    @Length(max = 1000)
    private String extension = null;

    public String getId() {
        return id;
    }

    public SearchEngine setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public SearchEngine setName(String name) {
        this.name = name;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public SearchEngine setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getExtension() {
        return extension;
    }

    public SearchEngine setExtension(String extension) {
        this.extension = extension;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SearchEngine {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    extension: ").append(toIndentedString(extension)).append("\n");
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
        SearchEngine searchEngine = (SearchEngine) o;
        return Objects.equals(this.id, searchEngine.id) && Objects.equals(this.name, searchEngine.name)
            && Objects.equals(this.url, searchEngine.url) && Objects.equals(this.extension, searchEngine.extension);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, url, extension);
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

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 自定义对象信息请求体定义
 */
@ApiModel(description = "自定义对象信息请求体定义")

@Validated

public class ObjectInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "对象名称", example = "自定义对象1", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("schemas")
    @Schema(description = "对象结构", example = "{\"key\":\"value\"}", required = true)
    @NotBlank
    private String schemas = null;

    @JsonProperty("description")
    @Schema(description = "对象描述", example = "对象描述信息")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("id")
    @Schema(description = "对象ID", example = "obj-001")
    @Length(max = 64)
    private String id = null;

    public String getName() {
        return name;
    }

    public ObjectInfoReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getSchemas() {
        return schemas;
    }

    public ObjectInfoReq setSchemas(String schemas) {
        this.schemas = schemas;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ObjectInfoReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getId() {
        return id;
    }

    public ObjectInfoReq setId(String id) {
        this.id = id;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ObjectInfoReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    schemas: ").append(toIndentedString(schemas)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        ObjectInfoReq objectInfoReq = (ObjectInfoReq) o;
        return Objects.equals(this.name, objectInfoReq.name) && Objects.equals(this.schemas, objectInfoReq.schemas)
            && Objects.equals(this.description, objectInfoReq.description) && Objects.equals(this.id, objectInfoReq.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, schemas, description, id);
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

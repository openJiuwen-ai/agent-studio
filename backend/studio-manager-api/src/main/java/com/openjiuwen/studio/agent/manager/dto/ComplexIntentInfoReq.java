/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 意图包信息定义
 */
@ApiModel(description = "意图包信息定义")

@Validated

public class ComplexIntentInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "意图包名称", example = "用户咨询意图", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "意图包描述", example = "处理用户咨询相关意图")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("id")
    @Schema(description = "意图包ID", example = "intent_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("branches")
    @Schema(description = "意图分支列表", example = "[]")
    @Valid
    @Size(max = 200)
    private List<ComplexIntentBranchInfoReq> branches = null;

    public String getName() {
        return name;
    }

    public ComplexIntentInfoReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ComplexIntentInfoReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getId() {
        return id;
    }

    public ComplexIntentInfoReq setId(String id) {
        this.id = id;
        return this;
    }

    public List<ComplexIntentBranchInfoReq> getBranches() {
        return branches;
    }

    public ComplexIntentInfoReq setBranches(List<ComplexIntentBranchInfoReq> branches) {
        this.branches = branches;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentInfoReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    branches: ").append(toIndentedString(branches)).append("\n");
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
        ComplexIntentInfoReq complexIntentInfoReq = (ComplexIntentInfoReq) o;
        return Objects.equals(this.name, complexIntentInfoReq.name) && Objects.equals(this.description,
            complexIntentInfoReq.description) && Objects.equals(this.id, complexIntentInfoReq.id) && Objects.equals(
            this.branches, complexIntentInfoReq.branches);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, id, branches);
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

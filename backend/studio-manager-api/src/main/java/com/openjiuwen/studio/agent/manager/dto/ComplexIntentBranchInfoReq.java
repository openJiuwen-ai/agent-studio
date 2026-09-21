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
 * 意图包分支信息定义
 */
@ApiModel(description = "意图包分支信息定义")

@Validated

public class ComplexIntentBranchInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "分支名称", example = "意图分支1", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "分支描述", example = "处理用户查询意图")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("examples")
    @Schema(description = "示例列表", example = "示例文本")
    @Valid
    @Size(max = 100)
    private List<@Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$") @Length(min = 1, max = 64) String> examples
        = null;

    @JsonProperty("branch_id")
    @Schema(description = "分支ID", example = "branch-001")
    @Length(max = 64)
    private String branchId = null;

    public String getName() {
        return name;
    }

    public ComplexIntentBranchInfoReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ComplexIntentBranchInfoReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<String> getExamples() {
        return examples;
    }

    public ComplexIntentBranchInfoReq setExamples(List<String> examples) {
        this.examples = examples;
        return this;
    }

    public String getBranchId() {
        return branchId;
    }

    public ComplexIntentBranchInfoReq setBranchId(String branchId) {
        this.branchId = branchId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentBranchInfoReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    examples: ").append(toIndentedString(examples)).append("\n");
        sb.append("    branchId: ").append(toIndentedString(branchId)).append("\n");
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
        ComplexIntentBranchInfoReq complexIntentBranchInfoReq = (ComplexIntentBranchInfoReq) o;
        return Objects.equals(this.name, complexIntentBranchInfoReq.name) && Objects.equals(this.description,
            complexIntentBranchInfoReq.description) && Objects.equals(this.examples,
            complexIntentBranchInfoReq.examples) && Objects.equals(this.branchId, complexIntentBranchInfoReq.branchId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, examples, branchId);
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

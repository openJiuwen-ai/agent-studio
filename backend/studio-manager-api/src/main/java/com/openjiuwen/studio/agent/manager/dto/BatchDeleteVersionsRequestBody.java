/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量删除版本请求体
 */
@ApiModel(description = "批量删除版本请求体")

@Validated

public class BatchDeleteVersionsRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_ids")
    @Schema(description = "待删除的版本ID列表", example = "[\"1787901244768\"]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 20)
    private List<@Pattern(regexp = "^[0-9]+$") @Length(min = 1, max = 64) String> versionIds
        = new ArrayList<String>();

    public List<@Pattern(regexp = "^[0-9]+$") @Length(min = 1, max = 64) String> getVersionIds() {
        return versionIds;
    }

    public BatchDeleteVersionsRequestBody setVersionIds(
        List<@Pattern(regexp = "^[0-9]+$") @Length(min = 1, max = 64) String> versionIds) {
        this.versionIds = versionIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteVersionsRequestBody {\n");

        sb.append("    versionIds: ").append(toIndentedString(versionIds)).append("\n");
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
        BatchDeleteVersionsRequestBody batchDeleteVersionsRequestBody = (BatchDeleteVersionsRequestBody) o;
        return Objects.equals(this.versionIds, batchDeleteVersionsRequestBody.versionIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionIds);
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

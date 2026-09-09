/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 批量删除请求体
 */
@ApiModel(description = "批量删除请求体")

@Validated

public class CommonBatchDeleteRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("ids")
    @Schema(description = "ids", example = "[]")
    @Valid
    @Size(max = 10)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(min = 1, max = 64) String> ids = null;

    public List<String> getIds() {
        return ids;
    }

    public CommonBatchDeleteRequestBody setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CommonBatchDeleteRequestBody {\n");

        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
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
        CommonBatchDeleteRequestBody commonBatchDeleteRequestBody = (CommonBatchDeleteRequestBody) o;
        return Objects.equals(this.ids, commonBatchDeleteRequestBody.ids);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ids);
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

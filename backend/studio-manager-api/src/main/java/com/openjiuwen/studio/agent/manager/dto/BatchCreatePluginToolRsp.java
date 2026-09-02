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
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量创建工具响应
 */
@ApiModel(description = "批量创建工具响应")

@Validated

public class BatchCreatePluginToolRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("ids")
    @Schema(description = "ids", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(max = 64) String> ids = new ArrayList<String>();

    @JsonProperty("count")
    @Schema(description = "数量", example = "10", required = true)
    @NotNull
    @Range(min = 0L)
    private Integer count = null;

    public List<String> getIds() {
        return ids;
    }

    public BatchCreatePluginToolRsp setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public Integer getCount() {
        return count;
    }

    public BatchCreatePluginToolRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchCreatePluginToolRsp {\n");

        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
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
        BatchCreatePluginToolRsp batchCreatePluginToolRsp = (BatchCreatePluginToolRsp) o;
        return Objects.equals(this.ids, batchCreatePluginToolRsp.ids) && Objects.equals(this.count,
            batchCreatePluginToolRsp.count);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ids, count);
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

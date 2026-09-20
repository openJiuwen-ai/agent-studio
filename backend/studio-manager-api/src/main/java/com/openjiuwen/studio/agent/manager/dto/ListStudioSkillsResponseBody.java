/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * ListStudioSkillsResponseBody
 */

@Validated

public class ListStudioSkillsResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("items")
    @Schema(description = "items", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(max = 50)
    private List<StudioSkillInfo> items = new ArrayList<StudioSkillInfo>();

    @JsonProperty("total")
    @Schema(description = "总数", example = "100", required = true)
    @NotNull
    @Range(min = 0L, max = 1000000L)
    private Integer total = null;

    public List<StudioSkillInfo> getItems() {
        return items;
    }

    public ListStudioSkillsResponseBody setItems(List<StudioSkillInfo> items) {
        this.items = items;
        return this;
    }

    public Integer getTotal() {
        return total;
    }

    public ListStudioSkillsResponseBody setTotal(Integer total) {
        this.total = total;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListStudioSkillsResponseBody {\n");

        sb.append("    items: ").append(toIndentedString(items)).append("\n");
        sb.append("    total: ").append(toIndentedString(total)).append("\n");
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
        ListStudioSkillsResponseBody listStudioSkillsResponseBody = (ListStudioSkillsResponseBody) o;
        return Objects.equals(this.items, listStudioSkillsResponseBody.items) && Objects.equals(this.total,
            listStudioSkillsResponseBody.total);
    }

    @Override
    public int hashCode() {
        return Objects.hash(items, total);
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

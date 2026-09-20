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
 * 关联关系列表。
 */
@ApiModel(description = "关联关系列表。")

@Validated

public class RelationList implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("relations")
    @Schema(description = "关系列表", example = "[]")
    @Valid
    @Size()
    private List<Relation> relations = null;

    public Long getCount() {
        return count;
    }

    public RelationList setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<Relation> getRelations() {
        return relations;
    }

    public RelationList setRelations(List<Relation> relations) {
        this.relations = relations;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RelationList {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    relations: ").append(toIndentedString(relations)).append("\n");
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
        RelationList relationList = (RelationList) o;
        return Objects.equals(this.count, relationList.count) && Objects.equals(this.relations, relationList.relations);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, relations);
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

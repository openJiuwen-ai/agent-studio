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
 * 自主动态规划场景。
 */
@ApiModel(description = "自主动态规划场景。")

@Validated

public class Scene implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "场景ID", example = "scene_001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "场景名称", example = "客服场景")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "场景描述", example = "处理用户客服咨询的场景")
    private String description = null;

    @JsonProperty("guidelines")
    @Schema(description = "场景指导原则列表", example = "[]")
    @Valid
    @Size()
    private List<Guideline> guidelines = null;

    @JsonProperty("relations")
    @Schema(description = "指导原则间的关系列表", example = "[]")
    @Valid
    @Size()
    private List<RelationInGuideLine> relations = null;

    public String getId() {
        return id;
    }

    public Scene setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public Scene setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public Scene setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<Guideline> getGuidelines() {
        return guidelines;
    }

    public Scene setGuidelines(List<Guideline> guidelines) {
        this.guidelines = guidelines;
        return this;
    }

    public List<RelationInGuideLine> getRelations() {
        return relations;
    }

    public Scene setRelations(List<RelationInGuideLine> relations) {
        this.relations = relations;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Scene {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    guidelines: ").append(toIndentedString(guidelines)).append("\n");
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
        Scene scene = (Scene) o;
        return Objects.equals(this.id, scene.id) && Objects.equals(this.name, scene.name) && Objects.equals(
            this.description, scene.description) && Objects.equals(this.guidelines, scene.guidelines) && Objects.equals(
            this.relations, scene.relations);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, guidelines, relations);
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

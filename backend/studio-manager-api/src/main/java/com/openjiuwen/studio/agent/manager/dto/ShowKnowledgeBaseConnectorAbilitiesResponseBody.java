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
 * 知识库检索配置的响应体
 */
@ApiModel(description = "知识库检索配置的响应体")

@Validated

public class ShowKnowledgeBaseConnectorAbilitiesResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("abilities")
    @Schema(description = "abilities", example = "[]")
    @Valid
    @Size(max = 10)
    private List<AbilityInfo> abilities = null;

    public List<AbilityInfo> getAbilities() {
        return abilities;
    }

    public ShowKnowledgeBaseConnectorAbilitiesResponseBody setAbilities(List<AbilityInfo> abilities) {
        this.abilities = abilities;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShowKnowledgeBaseConnectorAbilitiesResponseBody {\n");

        sb.append("    abilities: ").append(toIndentedString(abilities)).append("\n");
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
        ShowKnowledgeBaseConnectorAbilitiesResponseBody showKnowledgeBaseConnectorAbilitiesResponseBody
            = (ShowKnowledgeBaseConnectorAbilitiesResponseBody) o;
        return Objects.equals(this.abilities, showKnowledgeBaseConnectorAbilitiesResponseBody.abilities);
    }

    @Override
    public int hashCode() {
        return Objects.hash(abilities);
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

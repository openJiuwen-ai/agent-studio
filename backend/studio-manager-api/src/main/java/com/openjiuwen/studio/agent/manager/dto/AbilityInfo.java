/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库连接器的能力
 */
@ApiModel(description = "知识库连接器的能力")

@Validated

public class AbilityInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "能力ID", example = "abc123")
    @Length(max = 50)
    private String id = null;

    @JsonProperty("code")
    @Schema(description = "能力编码", example = "search")
    @Length(max = 50)
    private String code = null;

    @JsonProperty("name")
    @Schema(description = "能力名称", example = "搜索能力")
    @Length(max = 500)
    private String name = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "conn001")
    @Length(max = 50)
    private String connectorId = null;

    @JsonProperty("sub_ability")
    @Schema(description = "子能力", example = "sub_search")
    @Length(max = 10000)
    private String subAbility = null;

    @JsonProperty("description")
    @Schema(description = "能力描述", example = "用于搜索知识库")
    @Length(max = 500)
    private String description = null;

    public String getId() {
        return id;
    }

    public AbilityInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getCode() {
        return code;
    }

    public AbilityInfo setCode(String code) {
        this.code = code;
        return this;
    }

    public String getName() {
        return name;
    }

    public AbilityInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public AbilityInfo setConnectorId(String connectorId) {
        this.connectorId = connectorId;
        return this;
    }

    public String getSubAbility() {
        return subAbility;
    }

    public AbilityInfo setSubAbility(String subAbility) {
        this.subAbility = subAbility;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AbilityInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AbilityInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    connectorId: ").append(toIndentedString(connectorId)).append("\n");
        sb.append("    subAbility: ").append(toIndentedString(subAbility)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        AbilityInfo abilityInfo = (AbilityInfo) o;
        return Objects.equals(this.id, abilityInfo.id) && Objects.equals(this.code, abilityInfo.code) && Objects.equals(
            this.name, abilityInfo.name) && Objects.equals(this.connectorId, abilityInfo.connectorId) && Objects.equals(
            this.subAbility, abilityInfo.subAbility) && Objects.equals(this.description, abilityInfo.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, code, name, connectorId, subAbility, description);
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

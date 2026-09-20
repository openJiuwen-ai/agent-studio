/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ActionList
 */

@Validated

public class ActionList implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("actions")
    @Schema(description = "操作列表", example = "[]")
    @Valid
    @Size()
    private List<ActionBaseInfo> actions = null;

    public List<ActionBaseInfo> getActions() {
        return actions;
    }

    public ActionList setActions(List<ActionBaseInfo> actions) {
        this.actions = actions;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ActionList {\n");

        sb.append("    actions: ").append(toIndentedString(actions)).append("\n");
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
        ActionList actionList = (ActionList) o;
        return Objects.equals(this.actions, actionList.actions);
    }

    @Override
    public int hashCode() {
        return Objects.hash(actions);
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

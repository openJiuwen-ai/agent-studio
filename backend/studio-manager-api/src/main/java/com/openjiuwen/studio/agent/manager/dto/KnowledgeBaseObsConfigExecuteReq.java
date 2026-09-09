/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * OBS配置执行动作。
 */
@ApiModel(description = "OBS配置执行动作。")

@Validated

public class KnowledgeBaseObsConfigExecuteReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("action")
    @Schema(description = "操作", example = "STRING")
    private ActionEnum action = null;

    public ActionEnum getAction() {
        return action;
    }

    public KnowledgeBaseObsConfigExecuteReq setAction(ActionEnum action) {
        this.action = action;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseObsConfigExecuteReq {\n");

        sb.append("    action: ").append(toIndentedString(action)).append("\n");
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
        KnowledgeBaseObsConfigExecuteReq knowledgeBaseObsConfigExecuteReq = (KnowledgeBaseObsConfigExecuteReq) o;
        return Objects.equals(this.action, knowledgeBaseObsConfigExecuteReq.action);
    }

    @Override
    public int hashCode() {
        return Objects.hash(action);
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

    /**
     * OBS配置执行动作： - UPLOAD：上传
     */
    public enum ActionEnum {
        UPLOAD("UPLOAD");

        private String value;

        ActionEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ActionEnum fromValue(String text) {
            for (ActionEnum b : ActionEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}

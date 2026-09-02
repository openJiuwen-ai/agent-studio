/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * IR文件中工作流节点的用户画像记忆配置。
 */
@ApiModel(description = "IR文件中工作流节点的用户画像记忆配置。")

@Validated

public class WorkFlowNodeUserProfileIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("enable")
    @Schema(description = "enable", example = "true")
    private Boolean enable = false;

    public WorkFlowNodeUserProfileIR setEnable(Boolean enable) {
        this.enable = enable;
        return this;
    }

    public Boolean isEnable() {
        return enable;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkFlowNodeUserProfileIR {\n");

        sb.append("    enable: ").append(toIndentedString(enable)).append("\n");
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
        WorkFlowNodeUserProfileIR workFlowNodeUserProfileIR = (WorkFlowNodeUserProfileIR) o;
        return Objects.equals(this.enable, workFlowNodeUserProfileIR.enable);
    }

    @Override
    public int hashCode() {
        return Objects.hash(enable);
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

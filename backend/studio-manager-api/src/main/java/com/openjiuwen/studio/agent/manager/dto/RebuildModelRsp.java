/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 重构模型结果返回值。
 */
@ApiModel(description = "重构模型结果返回值。")

@Validated

public class RebuildModelRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("status")
    @Schema(description = "状态", example = "STRING")
    private StatusEnum status = null;

    @JsonProperty("failed_models")
    @Schema(description = "是否失败", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> failedModels = null;

    public StatusEnum getStatus() {
        return status;
    }

    public RebuildModelRsp setStatus(StatusEnum status) {
        this.status = status;
        return this;
    }

    public List<String> getFailedModels() {
        return failedModels;
    }

    public RebuildModelRsp setFailedModels(List<String> failedModels) {
        this.failedModels = failedModels;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RebuildModelRsp {\n");

        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    failedModels: ").append(toIndentedString(failedModels)).append("\n");
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
        RebuildModelRsp rebuildModelRsp = (RebuildModelRsp) o;
        return Objects.equals(this.status, rebuildModelRsp.status) && Objects.equals(this.failedModels,
            rebuildModelRsp.failedModels);
    }

    @Override
    public int hashCode() {
        return Objects.hash(status, failedModels);
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
     * 鉴权信息。
     */
    public enum StatusEnum {
        SUCCESS("SUCCESS"),

        FAILED("FAILED"),

        ALREADY_REBUILD("ALREADY REBUILD");

        private String value;

        StatusEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static StatusEnum fromValue(String text) {
            for (StatusEnum b : StatusEnum.values()) {
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

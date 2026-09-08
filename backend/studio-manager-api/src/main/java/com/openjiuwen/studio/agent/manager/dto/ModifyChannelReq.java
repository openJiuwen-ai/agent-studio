/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 修改应用版本通道请求体。
 */
@ApiModel(description = "修改应用版本通道请求体。")

@Validated

public class ModifyChannelReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(max = 128)
    private String versionId = null;

    @JsonProperty("visibility_scope")
    @Schema(description = "visibilityscope", example = "STRING")
    private VisibilityScopeEnum visibilityScope = VisibilityScopeEnum.TENANT;

    @JsonProperty("call_count")
    @Schema(description = "数量", example = "10")
    @Range(min = -1L, max = 10000L)
    private Integer callCount = null;

    public String getVersionId() {
        return versionId;
    }

    public ModifyChannelReq setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public VisibilityScopeEnum getVisibilityScope() {
        return visibilityScope;
    }

    public ModifyChannelReq setVisibilityScope(VisibilityScopeEnum visibilityScope) {
        this.visibilityScope = visibilityScope;
        return this;
    }

    public Integer getCallCount() {
        return callCount;
    }

    public ModifyChannelReq setCallCount(Integer callCount) {
        this.callCount = callCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyChannelReq {\n");

        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    visibilityScope: ").append(toIndentedString(visibilityScope)).append("\n");
        sb.append("    callCount: ").append(toIndentedString(callCount)).append("\n");
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
        ModifyChannelReq modifyChannelReq = (ModifyChannelReq) o;
        return Objects.equals(this.versionId, modifyChannelReq.versionId) && Objects.equals(this.visibilityScope,
            modifyChannelReq.visibilityScope) && Objects.equals(this.callCount, modifyChannelReq.callCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, visibilityScope, callCount);
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
     * 可见范围。
     */
    public enum VisibilityScopeEnum {
        ALL("ALL"),

        TENANT("TENANT");

        private String value;

        VisibilityScopeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static VisibilityScopeEnum fromValue(String text) {
            for (VisibilityScopeEnum b : VisibilityScopeEnum.values()) {
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

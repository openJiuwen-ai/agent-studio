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
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 创建应用版本通道请求体。
 */
@ApiModel(description = "创建应用版本通道请求体。")

@Validated

public class CreateChannelReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0")
    @Length(max = 10000)
    private String versionId = null;

    @JsonProperty("channel_type")
    @Schema(description = "通道类型", example = "WEB", required = true)
    @NotBlank
    @Length(max = 10000)
    private String channelType = null;

    @JsonProperty("sub_type")
    @Schema(description = "子类型", example = "chat")
    @Length(max = 100)
    private String subType = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据列表", example = "[\"meta1\"]")
    @Valid
    @Size(max = 2)
    private List<@Length(min = 1, max = 100) String> metadata = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFrontParam> inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出参数列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFrontParam> outputs = null;

    @JsonProperty("prologue")
    @Schema(description = "开场白", example = "你好，有什么可以帮您？")
    @Length(max = 1000000)
    private String prologue = null;

    @JsonProperty("suggest_queries")
    @Schema(description = "推荐问题列表", example = "[\"问题1\"]")
    @Valid
    @Size()
    private List<@Length() String> suggestQueries = null;

    @JsonProperty("visibility_scope")
    @Schema(description = "可见范围", example = "TENANT")
    private VisibilityScopeEnum visibilityScope = VisibilityScopeEnum.TENANT;

    @JsonProperty("call_count")
    @Schema(description = "调用次数", example = "100")
    @Range(min = -1L, max = 10000L)
    private Integer callCount = null;

    public String getVersionId() {
        return versionId;
    }

    public CreateChannelReq setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getChannelType() {
        return channelType;
    }

    public CreateChannelReq setChannelType(String channelType) {
        this.channelType = channelType;
        return this;
    }

    public String getSubType() {
        return subType;
    }

    public CreateChannelReq setSubType(String subType) {
        this.subType = subType;
        return this;
    }

    public List<String> getMetadata() {
        return metadata;
    }

    public CreateChannelReq setMetadata(List<String> metadata) {
        this.metadata = metadata;
        return this;
    }

    public List<WorkflowFrontParam> getInputs() {
        return inputs;
    }

    public CreateChannelReq setInputs(List<WorkflowFrontParam> inputs) {
        this.inputs = inputs;
        return this;
    }

    public List<WorkflowFrontParam> getOutputs() {
        return outputs;
    }

    public CreateChannelReq setOutputs(List<WorkflowFrontParam> outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getPrologue() {
        return prologue;
    }

    public CreateChannelReq setPrologue(String prologue) {
        this.prologue = prologue;
        return this;
    }

    public List<String> getSuggestQueries() {
        return suggestQueries;
    }

    public CreateChannelReq setSuggestQueries(List<String> suggestQueries) {
        this.suggestQueries = suggestQueries;
        return this;
    }

    public VisibilityScopeEnum getVisibilityScope() {
        return visibilityScope;
    }

    public CreateChannelReq setVisibilityScope(VisibilityScopeEnum visibilityScope) {
        this.visibilityScope = visibilityScope;
        return this;
    }

    public Integer getCallCount() {
        return callCount;
    }

    public CreateChannelReq setCallCount(Integer callCount) {
        this.callCount = callCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateChannelReq {\n");

        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    channelType: ").append(toIndentedString(channelType)).append("\n");
        sb.append("    subType: ").append(toIndentedString(subType)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    prologue: ").append(toIndentedString(prologue)).append("\n");
        sb.append("    suggestQueries: ").append(toIndentedString(suggestQueries)).append("\n");
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
        CreateChannelReq createChannelReq = (CreateChannelReq) o;
        return Objects.equals(this.versionId, createChannelReq.versionId) && Objects.equals(this.channelType,
            createChannelReq.channelType) && Objects.equals(this.subType, createChannelReq.subType) && Objects.equals(
            this.metadata, createChannelReq.metadata) && Objects.equals(this.inputs, createChannelReq.inputs)
            && Objects.equals(this.outputs, createChannelReq.outputs) && Objects.equals(this.prologue,
            createChannelReq.prologue) && Objects.equals(this.suggestQueries, createChannelReq.suggestQueries)
            && Objects.equals(this.visibilityScope, createChannelReq.visibilityScope) && Objects.equals(this.callCount,
            createChannelReq.callCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, channelType, subType, metadata, inputs, outputs, prologue, suggestQueries,
            visibilityScope, callCount);
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

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 工具列表
 */
@ApiModel(description = "工具列表")

@Validated

public class ComplexIntentListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1", required = true)
    @NotNull
    private Long count = null;

    @JsonProperty("intents")
    @Schema(description = "意图列表", example = "[]")
    @Valid
    @Size()
    private List<ComplexIntentRsp> intents = null;

    public Long getCount() {
        return count;
    }

    public ComplexIntentListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<ComplexIntentRsp> getIntents() {
        return intents;
    }

    public ComplexIntentListRsp setIntents(List<ComplexIntentRsp> intents) {
        this.intents = intents;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    intents: ").append(toIndentedString(intents)).append("\n");
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
        ComplexIntentListRsp complexIntentListRsp = (ComplexIntentListRsp) o;
        return Objects.equals(this.count, complexIntentListRsp.count) && Objects.equals(this.intents,
            complexIntentListRsp.intents);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, intents);
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

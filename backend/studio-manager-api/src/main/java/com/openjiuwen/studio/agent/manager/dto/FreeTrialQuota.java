/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * FreeTrialQuota
 */

@Validated

public class FreeTrialQuota implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    private Integer limit = null;

    @JsonProperty("usage")
    @Schema(description = "使用量", example = "1")
    private Integer usage = null;

    public Integer getLimit() {
        return limit;
    }

    public FreeTrialQuota setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public Integer getUsage() {
        return usage;
    }

    public FreeTrialQuota setUsage(Integer usage) {
        this.usage = usage;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FreeTrialQuota {\n");

        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    usage: ").append(toIndentedString(usage)).append("\n");
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
        FreeTrialQuota freeTrialQuota = (FreeTrialQuota) o;
        return Objects.equals(this.limit, freeTrialQuota.limit) && Objects.equals(this.usage, freeTrialQuota.usage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(limit, usage);
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

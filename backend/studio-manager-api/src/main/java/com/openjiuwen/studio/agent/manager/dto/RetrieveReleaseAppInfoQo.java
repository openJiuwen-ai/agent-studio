/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * RetrieveReleaseAppInfoQo: converted from multi query params
 */
@ApiModel(description = "RetrieveReleaseAppInfoQo: converted from multi query params")

@Validated

public class RetrieveReleaseAppInfoQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("find_by")
    @Schema(description = "findby", example = "示例字符串", required = true)
    @NotBlank
    private String findBy = null;

    @JsonProperty("channel_type")
    @Schema(description = "渠道类型", example = "example-type", required = true)
    @NotBlank
    private String channelType = null;

    public String getFindBy() {
        return findBy;
    }

    public RetrieveReleaseAppInfoQo setFindBy(String findBy) {
        this.findBy = findBy;
        return this;
    }

    public String getChannelType() {
        return channelType;
    }

    public RetrieveReleaseAppInfoQo setChannelType(String channelType) {
        this.channelType = channelType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RetrieveReleaseAppInfoQo {\n");

        sb.append("    findBy: ").append(toIndentedString(findBy)).append("\n");
        sb.append("    channelType: ").append(toIndentedString(channelType)).append("\n");
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
        RetrieveReleaseAppInfoQo retrieveReleaseAppInfoQo = (RetrieveReleaseAppInfoQo) o;
        return Objects.equals(this.findBy, retrieveReleaseAppInfoQo.findBy) && Objects.equals(this.channelType,
            retrieveReleaseAppInfoQo.channelType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(findBy, channelType);
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

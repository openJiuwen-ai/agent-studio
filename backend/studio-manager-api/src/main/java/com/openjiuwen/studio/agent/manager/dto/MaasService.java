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
 * MaasService
 */

@Validated

public class MaasService implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("served_model_name")
    @Schema(description = "模型", example = "示例名称")
    private String servedModelName = null;

    @JsonProperty("is_subscribed")
    @Schema(description = "issubscribed", example = "true")
    private Boolean isSubscribed = false;

    public String getServedModelName() {
        return servedModelName;
    }

    public MaasService setServedModelName(String servedModelName) {
        this.servedModelName = servedModelName;
        return this;
    }

    public MaasService setIsSubscribed(Boolean isSubscribed) {
        this.isSubscribed = isSubscribed;
        return this;
    }

    public Boolean isIsSubscribed() {
        return isSubscribed;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MaasService {\n");

        sb.append("    servedModelName: ").append(toIndentedString(servedModelName)).append("\n");
        sb.append("    isSubscribed: ").append(toIndentedString(isSubscribed)).append("\n");
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
        MaasService maasService = (MaasService) o;
        return Objects.equals(this.servedModelName, maasService.servedModelName) && Objects.equals(this.isSubscribed,
            maasService.isSubscribed);
    }

    @Override
    public int hashCode() {
        return Objects.hash(servedModelName, isSubscribed);
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

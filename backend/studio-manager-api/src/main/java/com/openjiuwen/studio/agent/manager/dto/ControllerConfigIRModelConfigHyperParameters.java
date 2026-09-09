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
 * ControllerConfigIRModelConfigHyperParameters
 */

@Validated

public class ControllerConfigIRModelConfigHyperParameters implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("temperature")
    @Schema(description = "温度参数", example = "0.7")
    private Float temperature = null;

    @JsonProperty("top_p")
    @Schema(description = "Top-P参数", example = "1.0")
    private Float topP = null;

    public Float getTemperature() {
        return temperature;
    }

    public ControllerConfigIRModelConfigHyperParameters setTemperature(Float temperature) {
        this.temperature = temperature;
        return this;
    }

    public Float getTopP() {
        return topP;
    }

    public ControllerConfigIRModelConfigHyperParameters setTopP(Float topP) {
        this.topP = topP;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerConfigIRModelConfigHyperParameters {\n");

        sb.append("    temperature: ").append(toIndentedString(temperature)).append("\n");
        sb.append("    topP: ").append(toIndentedString(topP)).append("\n");
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
        ControllerConfigIRModelConfigHyperParameters controllerConfigIRModelConfigHyperParameters
            = (ControllerConfigIRModelConfigHyperParameters) o;
        return Objects.equals(this.temperature, controllerConfigIRModelConfigHyperParameters.temperature)
            && Objects.equals(this.topP, controllerConfigIRModelConfigHyperParameters.topP);
    }

    @Override
    public int hashCode() {
        return Objects.hash(temperature, topP);
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

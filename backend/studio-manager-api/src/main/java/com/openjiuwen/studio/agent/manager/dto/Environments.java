/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 安全组列表
 */
@ApiModel(description = "安全组列表")

@Validated

public class Environments implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    private Integer total = null;

    @JsonProperty("env_info")
    @Schema(description = "环境", example = "[]")
    @Valid
    @Size()
    private List<Environment> envInfo = null;

    public Integer getTotal() {
        return total;
    }

    public Environments setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public List<Environment> getEnvInfo() {
        return envInfo;
    }

    public Environments setEnvInfo(List<Environment> envInfo) {
        this.envInfo = envInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Environments {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    envInfo: ").append(toIndentedString(envInfo)).append("\n");
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
        Environments environments = (Environments) o;
        return Objects.equals(this.total, environments.total) && Objects.equals(this.envInfo, environments.envInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, envInfo);
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

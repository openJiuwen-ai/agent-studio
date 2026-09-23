/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 修改环境请求体：PUT 修改语义为部分更新（仅更新 description），
 * name/vpcId/subnetId 由创建接口（EnvironmentInfoRequest）强制必填。
 */
@ApiModel(description = "修改环境请求体")

@Validated

public class ModifyEnvironmentInfoRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("description")
    @Schema(description = "安全组描述", example = "用于Agent运行的安全组")
    @Length(max = 1024)
    private String description = null;

    public String getDescription() {
        return description;
    }

    public ModifyEnvironmentInfoRequestBody setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        ModifyEnvironmentInfoRequestBody that = (ModifyEnvironmentInfoRequestBody) o;
        return Objects.equals(this.description, that.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(description);
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyEnvironmentInfoRequestBody {\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}

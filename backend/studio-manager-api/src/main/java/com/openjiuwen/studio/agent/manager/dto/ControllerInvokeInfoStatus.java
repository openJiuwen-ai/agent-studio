/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 节点执行的结果状态, 成功/失败
 */
@ApiModel(description = "节点执行的结果状态, 成功/失败")

@Validated

public class ControllerInvokeInfoStatus implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    private Integer code = null;

    @JsonProperty("desc")
    @Length(max = 1024)
    private String desc = null;

    public Integer getCode() {
        return code;
    }

    public ControllerInvokeInfoStatus setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public ControllerInvokeInfoStatus setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerInvokeInfoStatus {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
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
        ControllerInvokeInfoStatus controllerInvokeInfoStatus = (ControllerInvokeInfoStatus) o;
        return Objects.equals(this.code, controllerInvokeInfoStatus.code) && Objects.equals(this.desc,
            controllerInvokeInfoStatus.desc);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, desc);
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

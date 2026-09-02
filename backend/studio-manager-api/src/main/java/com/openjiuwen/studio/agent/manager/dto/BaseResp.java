/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * BaseResp
 */

@Validated

public class BaseResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "状态码", example = "200")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "操作成功")
    private String message = null;

    @JsonProperty("data")
    @Schema(description = "数据", example = "{}")
    @Valid
    private Object data = null;

    public Integer getCode() {
        return code;
    }

    public BaseResp setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public BaseResp setMessage(String message) {
        this.message = message;
        return this;
    }

    public Object getData() {
        return data;
    }

    public BaseResp setData(Object data) {
        this.data = data;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BaseResp {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
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
        BaseResp baseResp = (BaseResp) o;
        return Objects.equals(this.code, baseResp.code) && Objects.equals(this.message, baseResp.message)
            && Objects.equals(this.data, baseResp.data);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, message, data);
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

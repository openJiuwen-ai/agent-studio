/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

@Validated
public class JiuwenEventDataError implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("error_code")
    private Integer errorCode = null;

    @JsonProperty("message")
    private String message = null;

    public Integer getErrorCode() {
        return errorCode;
    }

    public JiuwenEventDataError setErrorCode(Integer errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public JiuwenEventDataError setMessage(String message) {
        this.message = message;
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
        JiuwenEventDataError that = (JiuwenEventDataError) o;
        return Objects.equals(this.errorCode, that.errorCode) && Objects.equals(this.message, that.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, message);
    }

    @Override
    public String toString() {
        return "JiuwenEventDataError{errorCode=" + errorCode + ", message='" + message + "'}";
    }
}

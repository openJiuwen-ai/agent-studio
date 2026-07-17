/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

@Validated
public class JiuwenEventDataInnerError implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("isSuccess")
    private Boolean isSuccess = null;

    @JsonProperty("errorBody")
    @Valid
    private JiuwenEventDataInnerErrorErrorBody errorBody = null;

    public JiuwenEventDataInnerError setIsSuccess(Boolean isSuccess) {
        this.isSuccess = isSuccess;
        return this;
    }

    public Boolean isIsSuccess() {
        return isSuccess;
    }

    public JiuwenEventDataInnerErrorErrorBody getErrorBody() {
        return errorBody;
    }

    public JiuwenEventDataInnerError setErrorBody(JiuwenEventDataInnerErrorErrorBody errorBody) {
        this.errorBody = errorBody;
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
        JiuwenEventDataInnerError that = (JiuwenEventDataInnerError) o;
        return Objects.equals(this.isSuccess, that.isSuccess) && Objects.equals(this.errorBody, that.errorBody);
    }

    @Override
    public int hashCode() {
        return Objects.hash(isSuccess, errorBody);
    }

    @Override
    public String toString() {
        return "JiuwenEventDataInnerError{isSuccess=" + isSuccess + ", errorBody=" + errorBody + "}";
    }
}

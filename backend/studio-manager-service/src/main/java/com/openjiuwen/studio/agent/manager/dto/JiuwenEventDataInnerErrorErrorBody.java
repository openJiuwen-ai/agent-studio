/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

@Validated
public class JiuwenEventDataInnerErrorErrorBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("errorCode")
    private String errorCode = null;

    @JsonProperty("errorMessage")
    private String errorMessage = null;

    public String getErrorCode() {
        return errorCode;
    }

    public JiuwenEventDataInnerErrorErrorBody setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public JiuwenEventDataInnerErrorErrorBody setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
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
        JiuwenEventDataInnerErrorErrorBody that = (JiuwenEventDataInnerErrorErrorBody) o;
        return Objects.equals(this.errorCode, that.errorCode) && Objects.equals(this.errorMessage, that.errorMessage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, errorMessage);
    }

    @Override
    public String toString() {
        return "JiuwenEventDataInnerErrorErrorBody{errorCode='" + errorCode + "', errorMessage='" + errorMessage + "'}";
    }
}

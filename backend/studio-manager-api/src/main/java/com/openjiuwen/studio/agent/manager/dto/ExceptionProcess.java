/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 工作流节点异常配置。
 */
@ApiModel(description = "工作流节点异常配置。")

@Validated

public class ExceptionProcess implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("timeout")
    @Schema(description = "超时时间（秒）", example = "30")
    private Double timeout = null;

    @JsonProperty("retry_times")
    @Schema(description = "重试次数", example = "1")
    @Range(min = 0L, max = 3L)
    private Integer retryTimes = null;

    @JsonProperty("handle_type")
    @Schema(description = "异常处理类型", example = "interrupt")
    private HandleTypeEnum handleType = null;

    @JsonProperty("default_outputs")
    @Schema(description = "默认输出参数", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> defaultOutputs = null;

    public Double getTimeout() {
        return timeout;
    }

    public ExceptionProcess setTimeout(Double timeout) {
        this.timeout = timeout;
        return this;
    }

    public Integer getRetryTimes() {
        return retryTimes;
    }

    public ExceptionProcess setRetryTimes(Integer retryTimes) {
        this.retryTimes = retryTimes;
        return this;
    }

    public HandleTypeEnum getHandleType() {
        return handleType;
    }

    public ExceptionProcess setHandleType(HandleTypeEnum handleType) {
        this.handleType = handleType;
        return this;
    }

    public Map<String, Object> getDefaultOutputs() {
        return defaultOutputs;
    }

    public ExceptionProcess setDefaultOutputs(Map<String, Object> defaultOutputs) {
        this.defaultOutputs = defaultOutputs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExceptionProcess {\n");

        sb.append("    timeout: ").append(toIndentedString(timeout)).append("\n");
        sb.append("    retryTimes: ").append(toIndentedString(retryTimes)).append("\n");
        sb.append("    handleType: ").append(toIndentedString(handleType)).append("\n");
        sb.append("    defaultOutputs: ").append(toIndentedString(defaultOutputs)).append("\n");
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
        ExceptionProcess exceptionProcess = (ExceptionProcess) o;
        return Objects.equals(this.timeout, exceptionProcess.timeout) && Objects.equals(this.retryTimes,
            exceptionProcess.retryTimes) && Objects.equals(this.handleType, exceptionProcess.handleType)
            && Objects.equals(this.defaultOutputs, exceptionProcess.defaultOutputs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(timeout, retryTimes, handleType, defaultOutputs);
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

    /**
     * 异常处理类型。
     */
    public enum HandleTypeEnum {
        INTERRUPT("interrupt"),

        DEFAULTOUTPUTS("defaultOutputs"),

        ERRORBRANCH("errorbranch");

        private String value;

        HandleTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static HandleTypeEnum fromValue(String text) {
            for (HandleTypeEnum b : HandleTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}

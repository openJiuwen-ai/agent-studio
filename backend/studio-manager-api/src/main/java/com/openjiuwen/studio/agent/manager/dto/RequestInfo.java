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
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 工具请求信息
 */
@ApiModel(description = "工具请求信息")

@Validated

public class RequestInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("url")
    @Schema(description = "请求地址", example = "https://example.com/api", required = true)
    @Pattern(regexp = "^(http|https)://(?![^/]*@)(?!.*\\.\\.)[^ ]*$")
    @NotBlank
    @Length(min = 8, max = 256)
    private String url = null;

    @JsonProperty("method")
    @Schema(description = "请求方法", example = "GET", required = true)
    @NotNull
    private MethodEnum method = null;

    @JsonProperty("headers")
    @Schema(description = "请求头", example = "{\"Content-Type\":\"application/json\"}")
    @Valid
    @Size()
    private Map<@Length(min = 1, max = 20000) String, @Length(min = 1, max = 20000) String> headers = null;

    @JsonProperty("path_params")
    @Schema(description = "路径参数", example = "{}")
    @Length(max = 2000)
    private String pathParams = null;

    @JsonProperty("input_schema")
    @Schema(description = "输入Schema", example = "{}")
    @Length(max = 200000)
    private String inputSchema = null;

    public String getUrl() {
        return url;
    }

    public RequestInfo setUrl(String url) {
        this.url = url;
        return this;
    }

    public MethodEnum getMethod() {
        return method;
    }

    public RequestInfo setMethod(MethodEnum method) {
        this.method = method;
        return this;
    }

    public Map<String, String> getHeaders() {
        return headers;
    }

    public RequestInfo setHeaders(Map<String, String> headers) {
        this.headers = headers;
        return this;
    }

    public String getPathParams() {
        return pathParams;
    }

    public RequestInfo setPathParams(String pathParams) {
        this.pathParams = pathParams;
        return this;
    }

    public String getInputSchema() {
        return inputSchema;
    }

    public RequestInfo setInputSchema(String inputSchema) {
        this.inputSchema = inputSchema;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RequestInfo {\n");

        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    method: ").append(toIndentedString(method)).append("\n");
        sb.append("    headers: ").append(toIndentedString(headers)).append("\n");
        sb.append("    pathParams: ").append(toIndentedString(pathParams)).append("\n");
        sb.append("    inputSchema: ").append(toIndentedString(inputSchema)).append("\n");
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
        RequestInfo requestInfo = (RequestInfo) o;
        return Objects.equals(this.url, requestInfo.url) && Objects.equals(this.method, requestInfo.method)
            && Objects.equals(this.headers, requestInfo.headers) && Objects.equals(this.pathParams,
            requestInfo.pathParams) && Objects.equals(this.inputSchema, requestInfo.inputSchema);
    }

    @Override
    public int hashCode() {
        return Objects.hash(url, method, headers, pathParams, inputSchema);
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
     * 工具调用方法
     */
    public enum MethodEnum {
        GET("GET"),

        POST("POST");

        private String value;

        MethodEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static MethodEnum fromValue(String text) {
            for (MethodEnum b : MethodEnum.values()) {
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

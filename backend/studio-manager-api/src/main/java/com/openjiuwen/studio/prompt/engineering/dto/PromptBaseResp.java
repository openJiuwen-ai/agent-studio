/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * PromptBaseResp
 */

@Validated
public class PromptBaseResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "状态码：200 表示业务成功，非 200 表示业务失败", example = "200")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息内容依接口而定：prompt/tasks 列表接口为任务统计 JSON 字符串（如 {\"TOTAL\":0,\"TEXT\":0,\"MULTI\":0}），其余接口为操作提示消息", example = "success")
    private String message = null;

    @JsonProperty("data")
    @Schema(description = "业务数据，结构依接口而定；prompt/tasks 列表接口为分页对象（含列表数据与 total/pageNum/pageSize/pages 分页元数据）", example = "{}")
    @Valid
    private Object data = null;

    public Integer getCode() {
        return code;
    }

    public PromptBaseResp setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public PromptBaseResp setMessage(String message) {
        this.message = message;
        return this;
    }

    public Object getData() {
        return data;
    }

    public PromptBaseResp setData(Object data) {
        this.data = data;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptBaseResp {\n");
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
        PromptBaseResp promptBaseResp = (PromptBaseResp) o;
        return Objects.equals(this.code, promptBaseResp.code) && Objects.equals(this.message, promptBaseResp.message)
            && Objects.equals(this.data, promptBaseResp.data);
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

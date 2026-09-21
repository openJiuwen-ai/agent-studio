/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * NotifyResp
 */

@Validated

public class NotifyResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("res_code")
    @Schema(description = "响应码", example = "0")
    @Length(max = 64)
    private String resCode = null;

    @JsonProperty("res_msg")
    @Schema(description = "响应消息", example = "success")
    @Length(max = 64)
    private String resMsg = null;

    @JsonProperty("result")
    @Schema(description = "结果", example = "success")
    @Length(max = 64)
    private String result = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "success")
    @Length(max = 64)
    private String status = null;

    @JsonProperty("module_name")
    @Schema(description = "模块名称", example = "module-1")
    @Length(max = 64)
    private String moduleName = null;

    public String getResCode() {
        return resCode;
    }

    public NotifyResp setResCode(String resCode) {
        this.resCode = resCode;
        return this;
    }

    public String getResMsg() {
        return resMsg;
    }

    public NotifyResp setResMsg(String resMsg) {
        this.resMsg = resMsg;
        return this;
    }

    public String getResult() {
        return result;
    }

    public NotifyResp setResult(String result) {
        this.result = result;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public NotifyResp setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getModuleName() {
        return moduleName;
    }

    public NotifyResp setModuleName(String moduleName) {
        this.moduleName = moduleName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class NotifyResp {\n");

        sb.append("    resCode: ").append(toIndentedString(resCode)).append("\n");
        sb.append("    resMsg: ").append(toIndentedString(resMsg)).append("\n");
        sb.append("    result: ").append(toIndentedString(result)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    moduleName: ").append(toIndentedString(moduleName)).append("\n");
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
        NotifyResp notifyResp = (NotifyResp) o;
        return Objects.equals(this.resCode, notifyResp.resCode) && Objects.equals(this.resMsg, notifyResp.resMsg)
            && Objects.equals(this.result, notifyResp.result) && Objects.equals(this.status, notifyResp.status)
            && Objects.equals(this.moduleName, notifyResp.moduleName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resCode, resMsg, result, status, moduleName);
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

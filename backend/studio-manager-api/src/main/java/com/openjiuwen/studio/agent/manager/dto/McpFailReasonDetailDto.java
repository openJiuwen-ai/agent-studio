/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * MCP 部署失败原因详情 (包含全量国际化文案)
 */
@ApiModel(description = "MCP 部署失败原因详情 (包含全量国际化文案)")

@Validated

public class McpFailReasonDetailDto implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "错误码", example = "DEPLOY_FAILED")
    private String code = null;

    @JsonProperty("message_cn")
    @Schema(description = "中文错误信息", example = "部署失败")
    private String messageCn = null;

    @JsonProperty("message_en")
    @Schema(description = "英文错误信息", example = "Deploy failed")
    private String messageEn = null;

    @JsonProperty("reason_cn")
    @Schema(description = "中文失败原因", example = "配置错误")
    private String reasonCn = null;

    @JsonProperty("reason_en")
    @Schema(description = "英文失败原因", example = "Configuration error")
    private String reasonEn = null;

    @JsonProperty("suggestion_cn")
    @Schema(description = "中文修复建议", example = "请检查配置")
    private String suggestionCn = null;

    @JsonProperty("suggestion_en")
    @Schema(description = "英文修复建议", example = "Please check configuration")
    private String suggestionEn = null;

    @JsonProperty("debug_info")
    @Schema(description = "调试信息", example = "Connection timeout")
    private String debugInfo = null;

    public String getCode() {
        return code;
    }

    public McpFailReasonDetailDto setCode(String code) {
        this.code = code;
        return this;
    }

    public String getMessageCn() {
        return messageCn;
    }

    public McpFailReasonDetailDto setMessageCn(String messageCn) {
        this.messageCn = messageCn;
        return this;
    }

    public String getMessageEn() {
        return messageEn;
    }

    public McpFailReasonDetailDto setMessageEn(String messageEn) {
        this.messageEn = messageEn;
        return this;
    }

    public String getReasonCn() {
        return reasonCn;
    }

    public McpFailReasonDetailDto setReasonCn(String reasonCn) {
        this.reasonCn = reasonCn;
        return this;
    }

    public String getReasonEn() {
        return reasonEn;
    }

    public McpFailReasonDetailDto setReasonEn(String reasonEn) {
        this.reasonEn = reasonEn;
        return this;
    }

    public String getSuggestionCn() {
        return suggestionCn;
    }

    public McpFailReasonDetailDto setSuggestionCn(String suggestionCn) {
        this.suggestionCn = suggestionCn;
        return this;
    }

    public String getSuggestionEn() {
        return suggestionEn;
    }

    public McpFailReasonDetailDto setSuggestionEn(String suggestionEn) {
        this.suggestionEn = suggestionEn;
        return this;
    }

    public String getDebugInfo() {
        return debugInfo;
    }

    public McpFailReasonDetailDto setDebugInfo(String debugInfo) {
        this.debugInfo = debugInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpFailReasonDetailDto {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    messageCn: ").append(toIndentedString(messageCn)).append("\n");
        sb.append("    messageEn: ").append(toIndentedString(messageEn)).append("\n");
        sb.append("    reasonCn: ").append(toIndentedString(reasonCn)).append("\n");
        sb.append("    reasonEn: ").append(toIndentedString(reasonEn)).append("\n");
        sb.append("    suggestionCn: ").append(toIndentedString(suggestionCn)).append("\n");
        sb.append("    suggestionEn: ").append(toIndentedString(suggestionEn)).append("\n");
        sb.append("    debugInfo: ").append(toIndentedString(debugInfo)).append("\n");
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
        McpFailReasonDetailDto mcpFailReasonDetailDto = (McpFailReasonDetailDto) o;
        return Objects.equals(this.code, mcpFailReasonDetailDto.code) && Objects.equals(this.messageCn,
            mcpFailReasonDetailDto.messageCn) && Objects.equals(this.messageEn, mcpFailReasonDetailDto.messageEn)
            && Objects.equals(this.reasonCn, mcpFailReasonDetailDto.reasonCn) && Objects.equals(this.reasonEn,
            mcpFailReasonDetailDto.reasonEn) && Objects.equals(this.suggestionCn, mcpFailReasonDetailDto.suggestionCn)
            && Objects.equals(this.suggestionEn, mcpFailReasonDetailDto.suggestionEn) && Objects.equals(this.debugInfo,
            mcpFailReasonDetailDto.debugInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, messageCn, messageEn, reasonCn, reasonEn, suggestionCn, suggestionEn, debugInfo);
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

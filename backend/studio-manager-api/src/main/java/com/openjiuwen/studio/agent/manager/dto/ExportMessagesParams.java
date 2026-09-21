/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 导出相关参数
 */
@ApiModel(description = "导出相关参数")

@Validated

public class ExportMessagesParams implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("messages_ids")
    @Schema(description = "消息列表", example = "[]")
    @Valid
    @Size(max = 200)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(max = 64) String> messagesIds = null;

    public List<String> getMessagesIds() {
        return messagesIds;
    }

    public ExportMessagesParams setMessagesIds(List<String> messagesIds) {
        this.messagesIds = messagesIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportMessagesParams {\n");

        sb.append("    messagesIds: ").append(toIndentedString(messagesIds)).append("\n");
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
        ExportMessagesParams exportMessagesParams = (ExportMessagesParams) o;
        return Objects.equals(this.messagesIds, exportMessagesParams.messagesIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(messagesIds);
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

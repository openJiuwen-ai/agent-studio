/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * LogContents
 */

@Validated

public class LogContents implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("content")
    @Schema(description = "日志内容", example = "服务启动成功")
    private String content = null;

    @JsonProperty("line_num")
    @Schema(description = "日志行号", example = "42")
    private String lineNum = null;

    @JsonProperty("createTime")
    @Schema(description = "创建时间", example = "2026-01-01T00:00:00Z")
    private String createTime = null;

    @JsonProperty("labels")
    @Schema(description = "日志标签", example = "{\"level\":\"INFO\"}")
    @Valid
    @Size()
    private Map<@Length() String, @Length() String> labels = null;

    public String getContent() {
        return content;
    }

    public LogContents setContent(String content) {
        this.content = content;
        return this;
    }

    public String getLineNum() {
        return lineNum;
    }

    public LogContents setLineNum(String lineNum) {
        this.lineNum = lineNum;
        return this;
    }

    public String getCreateTime() {
        return createTime;
    }

    public LogContents setCreateTime(String createTime) {
        this.createTime = createTime;
        return this;
    }

    public Map<String, String> getLabels() {
        return labels;
    }

    public LogContents setLabels(Map<String, String> labels) {
        this.labels = labels;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class LogContents {\n");

        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    lineNum: ").append(toIndentedString(lineNum)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    labels: ").append(toIndentedString(labels)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        LogContents logContents = (LogContents) obj;
        return Objects.equals(this.content, logContents.content) && Objects.equals(this.lineNum, logContents.lineNum)
            && Objects.equals(this.createTime, logContents.createTime) && Objects.equals(this.labels,
            logContents.labels);
    }

    @Override
    public int hashCode() {
        return Objects.hash(content, lineNum, createTime, labels);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}

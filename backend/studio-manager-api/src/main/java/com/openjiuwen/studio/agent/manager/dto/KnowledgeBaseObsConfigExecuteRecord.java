/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * OBS执行记录。
 */
@ApiModel(description = "OBS执行记录。")

@Validated

public class KnowledgeBaseObsConfigExecuteRecord implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "记录ID", example = "record-001")
    private String id = null;

    @JsonProperty("status")
    @Schema(description = "执行状态", example = "RUNNING")
    private StatusEnum status = null;

    @JsonProperty("start_time")
    @Schema(description = "开始时间", example = "1700000000000")
    private Long startTime = null;

    @JsonProperty("end_time")
    @Schema(description = "结束时间", example = "1700000001000")
    private Long endTime = null;

    @JsonProperty("log_detail")
    @Schema(description = "日志详情", example = "执行成功")
    private String logDetail = null;

    public String getId() {
        return id;
    }

    public KnowledgeBaseObsConfigExecuteRecord setId(String id) {
        this.id = id;
        return this;
    }

    public StatusEnum getStatus() {
        return status;
    }

    public KnowledgeBaseObsConfigExecuteRecord setStatus(StatusEnum status) {
        this.status = status;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public KnowledgeBaseObsConfigExecuteRecord setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public KnowledgeBaseObsConfigExecuteRecord setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getLogDetail() {
        return logDetail;
    }

    public KnowledgeBaseObsConfigExecuteRecord setLogDetail(String logDetail) {
        this.logDetail = logDetail;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseObsConfigExecuteRecord {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    logDetail: ").append(toIndentedString(logDetail)).append("\n");
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
        KnowledgeBaseObsConfigExecuteRecord knowledgeBaseObsConfigExecuteRecord
            = (KnowledgeBaseObsConfigExecuteRecord) o;
        return Objects.equals(this.id, knowledgeBaseObsConfigExecuteRecord.id) && Objects.equals(this.status,
            knowledgeBaseObsConfigExecuteRecord.status) && Objects.equals(this.startTime,
            knowledgeBaseObsConfigExecuteRecord.startTime) && Objects.equals(this.endTime,
            knowledgeBaseObsConfigExecuteRecord.endTime) && Objects.equals(this.logDetail,
            knowledgeBaseObsConfigExecuteRecord.logDetail);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, status, startTime, endTime, logDetail);
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
     * 执行状态： - RUNNING：执行中 - FINISHED：执行完成 - FAILED：执行失败
     */
    public enum StatusEnum {
        RUNNING("RUNNING"),

        FINISHED("FINISHED"),

        FAILED("FAILED");

        private String value;

        StatusEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static StatusEnum fromValue(String text) {
            for (StatusEnum b : StatusEnum.values()) {
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

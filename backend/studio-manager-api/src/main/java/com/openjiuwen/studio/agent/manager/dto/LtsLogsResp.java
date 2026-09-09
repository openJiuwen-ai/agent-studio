/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * LtsLogsResp
 */

@Validated

public class LtsLogsResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "日志总数", example = "100")
    private Integer count = null;

    @JsonProperty("isQueryComplete")
    @Schema(description = "查询是否完成", example = "true")
    private Boolean isQueryComplete = null;

    @JsonProperty("logs")
    @Schema(description = "日志列表", example = "[]")
    @Valid
    @Size()
    private List<LogContents> logs = null;

    @JsonProperty("analysisLogs")
    @Schema(description = "分析日志列表", example = "[]")
    @Valid
    @Size()
    private List<Object> analysisLogs = null;

    public Integer getCount() {
        return count;
    }

    public LtsLogsResp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public LtsLogsResp setIsQueryComplete(Boolean isQueryComplete) {
        this.isQueryComplete = isQueryComplete;
        return this;
    }

    public Boolean isIsQueryComplete() {
        return isQueryComplete;
    }

    public List<LogContents> getLogs() {
        return logs;
    }

    public LtsLogsResp setLogs(List<LogContents> logs) {
        this.logs = logs;
        return this;
    }

    public List<Object> getAnalysisLogs() {
        return analysisLogs;
    }

    public LtsLogsResp setAnalysisLogs(List<Object> analysisLogs) {
        this.analysisLogs = analysisLogs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class LtsLogsResp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    isQueryComplete: ").append(toIndentedString(isQueryComplete)).append("\n");
        sb.append("    logs: ").append(toIndentedString(logs)).append("\n");
        sb.append("    analysisLogs: ").append(toIndentedString(analysisLogs)).append("\n");
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
        LtsLogsResp ltsLogsResp = (LtsLogsResp) o;
        return Objects.equals(this.count, ltsLogsResp.count) && Objects.equals(this.isQueryComplete,
            ltsLogsResp.isQueryComplete) && Objects.equals(this.logs, ltsLogsResp.logs) && Objects.equals(
            this.analysisLogs, ltsLogsResp.analysisLogs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, isQueryComplete, logs, analysisLogs);
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

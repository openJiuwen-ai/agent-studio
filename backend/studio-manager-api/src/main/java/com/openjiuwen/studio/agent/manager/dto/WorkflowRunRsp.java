/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;

import com.openjiuwen.studio.agent.common.dto.agent.Status;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 工作流执行接口响应体。
 */
@ApiModel(description = "工作流执行接口响应体。")

@Validated

public class WorkflowRunRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("session_id")
    @Schema(description = "会话ID", example = "session_001")
    private String sessionId = null;

    @JsonProperty("outputs")
    @Schema(description = "输出结果", example = "{}", required = true)
    @Valid
    @NotNull
    @Size()
    private Map<String, Object> outputs = new HashMap<String, Object>();

    @JsonProperty("error_message")
    @Schema(description = "错误信息", example = "执行失败")
    @Length(max = 4096)
    private String errorMessage = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> metadata = null;

    @JsonProperty("status")
    @Schema(description = "执行状态", example = "SUCCESS")
    @Valid
    private Status status = null;

    @JsonProperty("start_time")
    @Schema(description = "开始时间", example = "1700000000000", required = true)
    @NotNull
    private Long startTime = null;

    @JsonProperty("end_time")
    @Schema(description = "结束时间", example = "1700000001000")
    private Long endTime = null;

    @JsonProperty("node_info")
    @Schema(description = "节点运行信息", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<NodeRunInfo> nodeInfo = new ArrayList<>();

    public String getSessionId() {
        return sessionId;
    }

    public WorkflowRunRsp setSessionId(String sessionId) {
        this.sessionId = sessionId;
        return this;
    }

    public Map<String, Object> getOutputs() {
        return outputs;
    }

    public WorkflowRunRsp setOutputs(Map<String, Object> outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public WorkflowRunRsp setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
        return this;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public WorkflowRunRsp setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        return this;
    }

    public Status getStatus() {
        return status;
    }

    public WorkflowRunRsp setStatus(Status status) {
        this.status = status;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public WorkflowRunRsp setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public WorkflowRunRsp setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public List<NodeRunInfo> getNodeInfo() {
        return nodeInfo;
    }

    public WorkflowRunRsp setNodeInfo(List<NodeRunInfo> nodeInfo) {
        this.nodeInfo = nodeInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowRunRsp {\n");

        sb.append("    sessionId: ").append(toIndentedString(sessionId)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    errorMessage: ").append(toIndentedString(errorMessage)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    nodeInfo: ").append(toIndentedString(nodeInfo)).append("\n");
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
        WorkflowRunRsp workflowRunRsp = (WorkflowRunRsp) o;
        return Objects.equals(this.sessionId, workflowRunRsp.sessionId) && Objects.equals(this.outputs,
            workflowRunRsp.outputs) && Objects.equals(this.errorMessage, workflowRunRsp.errorMessage) && Objects.equals(
            this.metadata, workflowRunRsp.metadata) && Objects.equals(this.status, workflowRunRsp.status)
            && Objects.equals(this.startTime, workflowRunRsp.startTime) && Objects.equals(this.endTime,
            workflowRunRsp.endTime) && Objects.equals(this.nodeInfo, workflowRunRsp.nodeInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(sessionId, outputs, errorMessage, metadata, status, startTime, endTime, nodeInfo);
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

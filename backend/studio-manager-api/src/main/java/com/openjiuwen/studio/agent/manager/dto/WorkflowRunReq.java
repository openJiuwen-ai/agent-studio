/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import com.openjiuwen.studio.agent.common.dto.WorkflowEnvironment;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * WorkflowRunReq
 */

@Validated

public class WorkflowRunReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("inputs")
    @Schema(description = "输入参数", example = "{\"query\":\"hello\"}")
    @Valid
    @Size()
    private Map<String, Object> inputs = null;

    @JsonProperty("globals")
    @Schema(description = "全局参数", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> globals = null;

    @JsonProperty("environment")
    @Schema(description = "运行环境", example = "{\"env\":\"prod\"}")
    @Valid
    private WorkflowEnvironment environment = null;

    @JsonProperty("messages")
    @Schema(description = "消息列表", example = "[{\"role\":\"user\",\"content\":\"hello\"}]")
    @Valid
    @Size()
    private List<Message> messages = null;

    public Map<String, Object> getInputs() {
        return inputs;
    }

    public WorkflowRunReq setInputs(Map<String, Object> inputs) {
        this.inputs = inputs;
        return this;
    }

    public Map<String, Object> getGlobals() {
        return globals;
    }

    public WorkflowRunReq setGlobals(Map<String, Object> globals) {
        this.globals = globals;
        return this;
    }

    public WorkflowEnvironment getEnvironment() {
        return environment;
    }

    public WorkflowRunReq setEnvironment(WorkflowEnvironment environment) {
        this.environment = environment;
        return this;
    }

    public List<Message> getMessages() {
        return messages;
    }

    public WorkflowRunReq setMessages(List<Message> messages) {
        this.messages = messages;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowRunReq {\n");

        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    globals: ").append(toIndentedString(globals)).append("\n");
        sb.append("    environment: ").append(toIndentedString(environment)).append("\n");
        sb.append("    messages: ").append(toIndentedString(messages)).append("\n");
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
        WorkflowRunReq workflowRunReq = (WorkflowRunReq) o;
        return Objects.equals(this.inputs, workflowRunReq.inputs) && Objects.equals(this.globals,
            workflowRunReq.globals) && Objects.equals(this.environment, workflowRunReq.environment) && Objects.equals(
            this.messages, workflowRunReq.messages);
    }

    @Override
    public int hashCode() {
        return Objects.hash(inputs, globals, environment, messages);
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

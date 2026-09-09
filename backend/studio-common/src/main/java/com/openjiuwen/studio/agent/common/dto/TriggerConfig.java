/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 触发器配置信息。
 */
@ApiModel(description = "触发器配置信息。")

@Validated

public class TriggerConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("trigger_id")
    @Schema(description = "触发器ID", example = "trigger_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String triggerId = null;

    @JsonProperty("name")
    @Schema(description = "触发器名称", example = "定时触发器", required = true)
    @Pattern(regexp = "^[a-zA-Z\\u4e00-\\u9fa5][a-zA-Z0-9_\\u4e00-\\u9fa5]{1,19}$")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "触发器类型", example = "cron", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String type = null;

    @JsonProperty("cron")
    @Schema(description = "Cron表达式", example = "0 0 * * * ?")
    @Length(max = 64)
    private String cron = null;

    @JsonProperty("prompt")
    @Schema(description = "触发提示词", example = "请执行定时任务")
    @Length(max = 5000)
    private String prompt = null;

    @JsonProperty("invocation")
    @Schema(description = "调用方式", example = "http://example.com/webhook")
    @Length(max = 500)
    private String invocation = null;

    @JsonProperty("params")
    @Schema(description = "触发器参数列表", example = "[]")
    @Valid
    @Size()
    private List<TriggerParam> params = null;

    @JsonProperty("hook_url")
    @Schema(description = "回调URL", example = "http://example.com/hook")
    @Length(max = 500)
    private String hookUrl = null;

    @JsonProperty("created_on")
    @Schema(description = "创建时间", example = "2026-09-01T12:00:00Z")
    private Date createdOn = null;

    public String getTriggerId() {
        return triggerId;
    }

    public TriggerConfig setTriggerId(String triggerId) {
        this.triggerId = triggerId;
        return this;
    }

    public String getName() {
        return name;
    }

    public TriggerConfig setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public TriggerConfig setType(String type) {
        this.type = type;
        return this;
    }

    public String getCron() {
        return cron;
    }

    public TriggerConfig setCron(String cron) {
        this.cron = cron;
        return this;
    }

    public String getPrompt() {
        return prompt;
    }

    public TriggerConfig setPrompt(String prompt) {
        this.prompt = prompt;
        return this;
    }

    public String getInvocation() {
        return invocation;
    }

    public TriggerConfig setInvocation(String invocation) {
        this.invocation = invocation;
        return this;
    }

    public List<TriggerParam> getParams() {
        return params;
    }

    public TriggerConfig setParams(List<TriggerParam> params) {
        this.params = params;
        return this;
    }

    public String getHookUrl() {
        return hookUrl;
    }

    public TriggerConfig setHookUrl(String hookUrl) {
        this.hookUrl = hookUrl;
        return this;
    }

    public Date getCreatedOn() {
        return createdOn;
    }

    public TriggerConfig setCreatedOn(Date createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TriggerConfig {\n");

        sb.append("    triggerId: ").append(toIndentedString(triggerId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    cron: ").append(toIndentedString(cron)).append("\n");
        sb.append("    prompt: ").append(toIndentedString(prompt)).append("\n");
        sb.append("    invocation: ").append(toIndentedString(invocation)).append("\n");
        sb.append("    params: ").append(toIndentedString(params)).append("\n");
        sb.append("    hookUrl: ").append(toIndentedString(hookUrl)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
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
        TriggerConfig triggerConfig = (TriggerConfig) o;
        return Objects.equals(this.triggerId, triggerConfig.triggerId) && Objects.equals(this.name, triggerConfig.name)
            && Objects.equals(this.type, triggerConfig.type) && Objects.equals(this.cron, triggerConfig.cron)
            && Objects.equals(this.prompt, triggerConfig.prompt) && Objects.equals(this.invocation,
            triggerConfig.invocation) && Objects.equals(this.params, triggerConfig.params) && Objects.equals(
            this.hookUrl, triggerConfig.hookUrl) && Objects.equals(this.createdOn, triggerConfig.createdOn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(triggerId, name, type, cron, prompt, invocation, params, hookUrl, createdOn);
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

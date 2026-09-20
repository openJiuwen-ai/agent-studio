/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建外部记忆服务实例响应体
 */
@ApiModel(description = "创建外部记忆服务实例响应体")
public class CreateMemoryServiceInstanceResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("instance_id")
    @Schema(description = "实例ID", example = "instance-001")
    private String instanceId = null;

    public String getInstanceId() {
        return instanceId;
    }

    public CreateMemoryServiceInstanceResponseBody setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CreateMemoryServiceInstanceResponseBody that = (CreateMemoryServiceInstanceResponseBody) o;
        return Objects.equals(this.instanceId, that.instanceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(instanceId);
    }

    @Override
    public String toString() {
        return "CreateMemoryServiceInstanceResponseBody{instanceId='" + instanceId + "'}";
    }
}

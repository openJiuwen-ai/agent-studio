/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建外部记忆服务实例请求体
 */
@ApiModel(description = "创建外部记忆服务实例请求体")

@Validated

public class CreateMemoryServiceInstanceRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "实例名称", example = "我的记忆服务", required = true)
    @NotBlank
    @Length(min = 1, max = 128)
    private String name = null;

    @JsonProperty("base_url")
    @Schema(description = "agent-memory服务地址", example = "http://mem-svc-a:8000", required = true)
    @NotBlank
    @Size(max = 512)
    private String baseUrl = null;

    @JsonProperty("api_key")
    @Schema(description = "MEMORY_API_KEY，加密存储，不入IR", example = "sk-xxxx")
    private String apiKey = null;

    @JsonProperty("deploy_meta")
    @Schema(description = "展示用JSON：vector_store_type/db_type等")
    private String deployMeta = null;

    public String getName() {
        return name;
    }

    public CreateMemoryServiceInstanceRequestBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public CreateMemoryServiceInstanceRequestBody setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
        return this;
    }

    public String getApiKey() {
        return apiKey;
    }

    public CreateMemoryServiceInstanceRequestBody setApiKey(String apiKey) {
        this.apiKey = apiKey;
        return this;
    }

    public String getDeployMeta() {
        return deployMeta;
    }

    public CreateMemoryServiceInstanceRequestBody setDeployMeta(String deployMeta) {
        this.deployMeta = deployMeta;
        return this;
    }

    @Override
    public String toString() {
        return "CreateMemoryServiceInstanceRequestBody{"
            + "name='" + name + '\''
            + ", baseUrl='" + baseUrl + '\''
            + ", apiKey='***'"
            + ", deployMeta='" + deployMeta + '\''
            + '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CreateMemoryServiceInstanceRequestBody that = (CreateMemoryServiceInstanceRequestBody) o;
        return Objects.equals(this.name, that.name)
            && Objects.equals(this.baseUrl, that.baseUrl)
            && Objects.equals(this.apiKey, that.apiKey)
            && Objects.equals(this.deployMeta, that.deployMeta);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, baseUrl, apiKey, deployMeta);
    }
}

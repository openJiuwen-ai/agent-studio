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
 * 修改外部记忆服务实例请求体
 */
@ApiModel(description = "修改外部记忆服务实例请求体")
@Validated
public class ModifyMemoryServiceInstanceRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "实例名称", example = "我的记忆服务")
    @Length(min = 1, max = 128)
    private String name = null;

    @JsonProperty("base_url")
    @Schema(description = "agent-memory服务地址", example = "http://mem-svc-a:8000")
    @Size(max = 512)
    private String baseUrl = null;

    @JsonProperty("api_key")
    @Schema(description = "MEMORY_API_KEY，加密存储，不入IR。为空表示不修改")
    private String apiKey = null;

    @JsonProperty("deploy_meta")
    @Schema(description = "展示用JSON：vector_store_type/db_type等")
    private String deployMeta = null;

    public String getName() {
        return name;
    }

    public ModifyMemoryServiceInstanceRequestBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public ModifyMemoryServiceInstanceRequestBody setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
        return this;
    }

    public String getApiKey() {
        return apiKey;
    }

    public ModifyMemoryServiceInstanceRequestBody setApiKey(String apiKey) {
        this.apiKey = apiKey;
        return this;
    }

    public String getDeployMeta() {
        return deployMeta;
    }

    public ModifyMemoryServiceInstanceRequestBody setDeployMeta(String deployMeta) {
        this.deployMeta = deployMeta;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        ModifyMemoryServiceInstanceRequestBody that = (ModifyMemoryServiceInstanceRequestBody) o;
        return Objects.equals(this.name, that.name)
            && Objects.equals(this.baseUrl, that.baseUrl)
            && Objects.equals(this.apiKey, that.apiKey)
            && Objects.equals(this.deployMeta, that.deployMeta);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, baseUrl, apiKey, deployMeta);
    }

    @Override
    public String toString() {
        return "ModifyMemoryServiceInstanceRequestBody{"
            + "name='" + name + '\''
            + ", baseUrl='" + baseUrl + '\''
            + ", apiKey='***'"
            + ", deployMeta='" + deployMeta + '\''
            + '}';
    }
}

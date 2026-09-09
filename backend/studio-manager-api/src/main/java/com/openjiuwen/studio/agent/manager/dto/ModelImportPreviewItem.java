/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;

/**
 * 模型导入预检单行结果（不落库，仅解析+冲突检测+URL 校验）。
 */
@ApiModel(description = "模型导入预检单行结果")
public class ModelImportPreviewItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "行ID", example = "row_001")
    private String id;

    @JsonProperty("service_name")
    @Schema(description = "模型服务名称", example = "gpt-4")
    private String serviceName;

    @JsonProperty("provider_id")
    @Schema(description = "供应商ID", example = "provider_001")
    private String providerId;

    @JsonProperty("conflict")
    @Schema(description = "是否存在冲突", example = "false")
    private Boolean conflict;

    /**
     * 本行是否合法（解析/import_type 校验通过）。false 时该行不可导入，前端禁用"确认导入"按钮。
     * 解析失败或 import_type 错时置 false；其他路径（URL/占位符/冲突）为警告而非硬错误，保持 true。
     */
    @JsonProperty("line_valid")
    @Schema(description = "本行是否合法", example = "true")
    private Boolean lineValid;

    @JsonProperty("api_url_valid")
    @Schema(description = "API URL是否有效", example = "true")
    private Boolean apiUrlValid;

    @JsonProperty("env_var_valid")
    @Schema(description = "环境变量是否有效", example = "true")
    private Boolean envVarValid;

    @JsonProperty("detail")
    @Schema(description = "详细信息", example = "URL格式不正确")
    private String detail;

    /**
     * 行类型：MODEL=模型行，PROVIDER=空供应商壳行（无模型、仅 upsert 供应商）。
     * 前端据全表 type 判断第一列标题：全 PROVIDER→供应商名称，否则→模型服务名称。
     */
    @JsonProperty("type")
    @Schema(description = "行类型", example = "MODEL")
    private String type;

    public String getId() {
        return id;
    }

    public ModelImportPreviewItem setId(String id) {
        this.id = id;
        return this;
    }

    public String getServiceName() {
        return serviceName;
    }

    public ModelImportPreviewItem setServiceName(String serviceName) {
        this.serviceName = serviceName;
        return this;
    }

    public String getProviderId() {
        return providerId;
    }

    public ModelImportPreviewItem setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public Boolean getConflict() {
        return conflict;
    }

    public ModelImportPreviewItem setConflict(Boolean conflict) {
        this.conflict = conflict;
        return this;
    }

    public Boolean getLineValid() {
        return lineValid;
    }

    public ModelImportPreviewItem setLineValid(Boolean lineValid) {
        this.lineValid = lineValid;
        return this;
    }

    public Boolean getApiUrlValid() {
        return apiUrlValid;
    }

    public ModelImportPreviewItem setApiUrlValid(Boolean apiUrlValid) {
        this.apiUrlValid = apiUrlValid;
        return this;
    }

    public Boolean getEnvVarValid() {
        return envVarValid;
    }

    public ModelImportPreviewItem setEnvVarValid(Boolean envVarValid) {
        this.envVarValid = envVarValid;
        return this;
    }

    public String getDetail() {
        return detail;
    }

    public ModelImportPreviewItem setDetail(String detail) {
        this.detail = detail;
        return this;
    }

    public String getType() {
        return type;
    }

    public ModelImportPreviewItem setType(String type) {
        this.type = type;
        return this;
    }
}

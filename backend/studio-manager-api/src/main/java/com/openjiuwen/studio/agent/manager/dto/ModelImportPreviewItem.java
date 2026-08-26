/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.annotations.ApiModel;

import java.io.Serializable;

/**
 * 模型导入预检单行结果（不落库，仅解析+验签+冲突检测）。
 */
@ApiModel(description = "模型导入预检单行结果")
public class ModelImportPreviewItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    private String id;

    @JsonProperty("service_name")
    private String serviceName;

    @JsonProperty("provider_id")
    private String providerId;

    @JsonProperty("conflict")
    private Boolean conflict;

    @JsonProperty("signature_valid")
    private Boolean signatureValid;

    @JsonProperty("api_url_valid")
    private Boolean apiUrlValid;

    @JsonProperty("env_var_valid")
    private Boolean envVarValid;

    /**
     * 鉴权加密方式是否被当前环境适配。true=明文/MASKED（可正常导入），false=文件包含加密鉴权且当前环境无解密能力（需用户在目标环境重新配置密钥）。
     */
    @JsonProperty("cipher_adapted")
    private Boolean cipherAdapted;

    @JsonProperty("detail")
    private String detail;

    /**
     * 行类型：MODEL=模型行，PROVIDER=空供应商壳行（无模型、仅 upsert 供应商）。
     * 前端据全表 type 判断第一列标题：全 PROVIDER→供应商名称，否则→模型服务名称。
     */
    @JsonProperty("type")
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

    public Boolean getSignatureValid() {
        return signatureValid;
    }

    public ModelImportPreviewItem setSignatureValid(Boolean signatureValid) {
        this.signatureValid = signatureValid;
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

    public Boolean getCipherAdapted() {
        return cipherAdapted;
    }

    public ModelImportPreviewItem setCipherAdapted(Boolean cipherAdapted) {
        this.cipherAdapted = cipherAdapted;
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

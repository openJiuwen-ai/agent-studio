/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.List;

/**
 * 模型批量导出请求体。
 *
 * <p>两种导出方式（原始需求要求支持）：
 * <ul>
 *   <li>按模型 id 列表导出：{@code model_ids} 非空，{@code include_provider} 控制是否带供应商元数据
 *       （true=供应商+模型，false=只导模型）。</li>
 *   <li>按供应商导出（卡片入口）：{@code provider_id} 非空，导出该供应商+其下全部模型（始终带供应商）。</li>
 * </ul>
 * {@code model_ids} 与 {@code provider_id} 二选一非空（controller 层校验）。
 */
@Schema(description = "模型批量导出请求体")
public class ModelExportReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("model_ids")
    @Schema(description = "模型", example = "[]")
    private List<String> modelIds;

    @JsonProperty("provider_id")
    @Schema(description = "按供应商导出（供应商+其下全部模型），与 model_ids 二选一", example = "example-id-123")
    private String providerId;

    @JsonProperty("include_provider")
    @Schema(description = "是否带供应商元数据；仅对 model_ids 方式生效，默认 true", example = "true")
    private Boolean includeProvider;

    public List<String> getModelIds() {
        return modelIds;
    }

    public ModelExportReq setModelIds(List<String> modelIds) {
        this.modelIds = modelIds;
        return this;
    }

    public String getProviderId() {
        return providerId;
    }

    public ModelExportReq setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public Boolean getIncludeProvider() {
        return includeProvider;
    }

    public ModelExportReq setIncludeProvider(Boolean includeProvider) {
        this.includeProvider = includeProvider;
        return this;
    }

    /** include_provider 缺省为 true（供应商+模型）。 */
    public boolean effectiveIncludeProvider() {
        return includeProvider == null || includeProvider;
    }
}

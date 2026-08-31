
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;

import lombok.Data;

import java.util.List;

@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ModelExportEntity {

    @JsonProperty("model_metadata")
    private List<ModelServiceData> modelMetadata;

    @JsonProperty("provider_metadata")
    private ProviderExportMetadata providerMetadata;

    /**
     * 导出模式标记：true=只导模型（includeProvider=false，不含供应商元数据）；
     * false=供应商+模型（缺省）。仅在 true 时序列化输出（{@link JsonInclude.Include#NON_DEFAULT}），
     * 使旧文件（无此字段）反序列化为 false 且重序列化时不输出该字段——签名验签与旧文件完全兼容。
     * 导入侧据此标记拦截"只导模型文件误导入列表页（无 targetProviderId）"的孤儿落库场景。
     */
    @JsonProperty("model_only")
    @JsonInclude(JsonInclude.Include.NON_DEFAULT)
    private boolean modelOnly;

}

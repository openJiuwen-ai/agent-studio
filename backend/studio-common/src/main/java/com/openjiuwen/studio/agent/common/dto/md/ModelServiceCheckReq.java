/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto.md;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

import java.util.Map;

@Getter
@Setter
@Accessors(chain = true)
@NoArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ModelServiceCheckReq {
    @NotNull
    private String modelType;

    @NotNull
    private String apiUrl;

    @NotNull
    private String authType;

    @NotNull
    private Map<String, String> authInfo;

    @NotNull
    private String modelName;

    @NotNull
    private String interfaceProtocol;

    /**
     * 重写 setter 对 apiUrl 做 trim，避免复制粘贴引入的前后空白导致下游 httpx 判为缺协议。
     * Lombok {@code @Setter} 检测到手动 setter 后不再为该字段生成 setter。
     */
    public ModelServiceCheckReq setApiUrl(String apiUrl) {
        this.apiUrl = apiUrl == null ? null : apiUrl.trim();
        return this;
    }
}

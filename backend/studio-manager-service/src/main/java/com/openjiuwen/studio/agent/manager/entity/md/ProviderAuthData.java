/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.md;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

/**
 * 供应商鉴权数据（API Key 等）。
 *
 * <p>{@code cipherName} 字段仅用于导入时识别加密鉴权标记——当前环境仅适配 NoOp（明文/MASKED），
 * 任何非空且不含 "NO_OP" 的 cipherName 表示文件来自支持加密导出的环境、当前环境无法解密，
 * 预检会标记 cipher_adapted=false 并阻止导入。本字段无 DB 列映射、本环境导出时恒为 null。
 */
@Getter
@Setter
@Accessors(chain = true)
@NoArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
@JsonIgnoreProperties(ignoreUnknown = true)
public class ProviderAuthData {
    private String id;

    private String providerId;

    private String authMetadataId;

    private String authType;

    private String authInfo;

    private String createdByUser;

    private long createdDate;

    private long lastUpdatedDate;

    private String domainId;

    private String projectId;

    private String workspaceId;

    private String identityId;

    /**
     * 加密方式标记（仅导入识别用；本环境导出时恒为 null，不会写入导出文件）。
     * <ul>
     *   <li>null / 空 / 含 "NO_OP"（如 NoOpCipher.name()="NO_OP_CIPHER" / "NoOp"）—— 明文 / MASKED 占位，当前环境可处理</li>
     *   <li>其他值（如 "AesGcm" / "AES_GCM"）—— 文件由支持加密导出的环境生成，当前环境未适配解密</li>
     * </ul>
     * 不持久化：该字段无 DB 列映射，仅在导入/导出 JSON 中作为识别标记存在。
     */
    @JsonProperty("cipher_name")
    private String cipherName;
}

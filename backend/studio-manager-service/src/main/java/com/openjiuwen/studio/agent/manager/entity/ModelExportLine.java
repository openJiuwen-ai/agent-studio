/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 模型导出 JSONL 行 DTO：包装 {@link ModelExportEntity} 并附加 HMAC 签名。
 *
 * <p>签名注入惯例（与 {@code AgentImportExportService} 的签名注入一致，两端必须用同一个
 * {@code jacksonObjectMapper}）：
 * <ul>
 *   <li>导出端：{@code payload} 置好 → {@code signature} 置 null → 序列化 → 计算签名 → 回填 signature → 再序列化写流</li>
 *   <li>验签端：取出 signature → 置 null → 序列化（与导出端计算签名时的字节一致）→ {@code verifySignature}</li>
 * </ul>
 * {@code @JsonInclude(NON_NULL)} 确保 {@code signature=null} 时该字段不出现，
 * 从而导出端「计算签名时的序列化」与验签端「重序列化」字节对齐，保证 round-trip。
 *
 * <p>{@code @JsonIgnoreProperties(ignoreUnknown = true)} 用于前向兼容：导入时忽略文件中未知的额外字段，
 * 避免因导出端新增字段导致旧导入端解析失败。
 *
 * <p>{@code importType}（{@code import_type}）类型标识：导出端置 {@code MODEL_SERVICE}，导入端据此
 * 拒绝非模型文件（如工作流/agent 的 {@code import_type} 为 {@code workflow}/{@code agent}）。旧模型导出
 * 文件无此字段 → 反序列化为 null → 导入端放行（向后兼容）。{@code @JsonInclude(NON_NULL)} 使旧文件
 * round-trip 时该字段仍不出现，验签字节不变。
 */
@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelExportLine {
    @JsonProperty("import_type")
    private String importType;

    private String signature;

    private ModelExportEntity payload;
}

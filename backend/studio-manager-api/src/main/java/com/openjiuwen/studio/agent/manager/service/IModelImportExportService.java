/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.enums.ModelImportConflictStrategy;

import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 模型服务批量导入/导出服务。
 *
 * <p>独立于「路径 B 资源适配器」框架（AgentExportService/AgentImportService/ModelAdapter），
 * 复用下层构件 {@code buildModelExportEntity} / {@code SignatureUtils} / {@code UrlCheckUtils} /
 * {@code ImportRsp}。导出走 JSONL + 逐行 HMAC 签名；导入落库用 {@code ModelServiceManager}
 * 保留跨环境 id。
 */
public interface IModelImportExportService {

    /**
     * 批量导出模型为签名 JSONL（供应商+模型，includeProvider=true）。旧签名，委托下行。
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param modelIds 待导出的模型 id 列表
     * @return JSONL 字节内容（controller 负责设置下载响应头）
     */
    byte[] exportModels(String projectId, String workspaceId, List<String> modelIds);

    /**
     * 批量导出模型为签名 JSONL，按 {@code includeProvider} 区分两种模式：
     * <ul>
     *   <li>{@code true}（缺省）— 供应商+模型：payload 含 provider_metadata。</li>
     *   <li>{@code false} — 只导模型：payload 的 provider_metadata=null（模型本身无密钥，api-key 在供应商侧，
     *       导出文件不含任何凭据；导入时把模型挂到目标环境已存在的供应商）。</li>
     * </ul>
     *
     * @param includeProvider 是否带供应商元数据
     */
    byte[] exportModels(String projectId, String workspaceId, List<String> modelIds, boolean includeProvider);

    /**
     * 按供应商导出（供应商列表页卡片入口）：导出该供应商 + 其下全部模型（始终带供应商）。
     *
     * @param providerId 供应商 id
     * @return JSONL 字节内容
     */
    byte[] exportModelsByProvider(String projectId, String workspaceId, String providerId);

    /**
     * 导入预检：逐行验签+解析+冲突检测+URL/占位符校验，<b>不落库</b>。旧签名，委托下行（targetProviderId=null）。
     */
    ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file);

    /**
     * 导入预检（支持「只导模型」重定向）。
     *
     * @param targetProviderId 目标供应商 id（详情页导入用）：当行 provider_metadata 为 null 且该值非空时，
     *                         预检把模型 providerId 重定向到该供应商，冲突判定用重定向后的值。列表页导入传 null。
     */
    ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file,
        String targetProviderId);

    /**
     * 导入落库：逐行验签+解析，按冲突策略 SKIP/COVER 落库，保留导入 id（跨环境一致）。旧签名，委托下行。
     */
    ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        ModelImportConflictStrategy conflictStrategy);

    /**
     * 导入落库（支持「只导模型」重定向）。
     *
     * @param targetProviderId 目标供应商 id（详情页导入用）：当行 provider_metadata 为 null 且该值非空时，
     *                         模型 providerId/authMetadataId 重定向到目标供应商（不 upsert 供应商）。
     *                         列表页导入传 null（走供应商+模型 upsert 路径）。
     */
    ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        ModelImportConflictStrategy conflictStrategy, String targetProviderId);
}

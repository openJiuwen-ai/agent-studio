/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service;

import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectionEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectionParam;
import com.openjiuwen.studio.agent.agentbase.model.obs.KbConnectionObsData;
import com.openjiuwen.studio.agent.agentbase.model.obs.KbKnowledgeBaseObsData;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.foundation.base.utils.JacksonUtils;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 知识库连接信息OBS存储服务
 * <p>
 * 连接文件和知识库文件分别存储，修改连接时只需更新连接文件，无需遍历所有关联的知识库文件。
 * 存储结构：
 * - kb-connection/ir/connection/{connectionId}.json       连接信息（独立文件）
 * - kb-connection/ir/knowledge-base/{knowledgeBaseId}.json 知识库信息（仅含知识库自身信息 + connectionId 引用）
 * </p>
 *
 * @since 2026-06-18
 */
@Slf4j
@Service
public class KbConnectionStorageService {

    private static final String CONNECTION_PATH = "kb-connection/ir/connection/%s.json";

    private static final String KNOWLEDGE_BASE_PATH = "kb-connection/ir/knowledge-base/%s.json";

    /**
     * 知识源模式（LakeSearch/KooSearch/CUSTOM）。
     * 写入 OBS 连接文件供 Python 端在检索时判断是否走 CUSTOM 专属语义。
     */
    @Value("${knowledge.source:LakeSearch}")
    private String knowledgeSource;

    private final MgObsService mgObsService;

    public KbConnectionStorageService(MgObsService mgObsService) {
        this.mgObsService = mgObsService;
    }

    // ==================== 连接文件操作（独立文件） ====================

    /**
     * 将连接信息写入OBS（独立文件）
     * <p>
     * 每个连接一个文件，修改连接时只需更新此文件，无需刷新关联的知识库文件。
     * </p>
     *
     * @param connection 连接实体（params中的敏感字段应已加密）
     * @param connectorType 连接器类型（inside/Outside）
     * @param connectorName 连接器名称
     */
    public void writeConnectionToObs(KnowledgeBaseConnectionEntity connection, String connectorType,
        String connectorName) {
        writeConnectionToObs(connection, connectorType, connectorName, null);
    }

    /**
     * 将连接信息写入OBS（独立文件），支持注入额外的配置参数
     * <p>
     * 用于默认 LakeSearch 连接场景：YAML 配置中的 project_id 和 application_id
     * 不在数据库 params 中，需要通过 extraParams 注入到 OBS 连接文件中，
     * 以便 Python 运行时能从连接文件获取完整信息。
     * </p>
     * <p>
     * 连接文件中同时包含该连接下所有知识库的 knowledgeBaseId → externalId 映射，
     * Python 运行时无需再读取单独的知识库文件即可获取 externalId（即 LakeSearch 的 repo_id）。
     * </p>
     *
     * @param connection 连接实体（params中的敏感字段应已加密）
     * @param connectorType 连接器类型（inside/Outside）
     * @param connectorName 连接器名称
     * @param extraParams 额外的配置参数（如 project_id、application_id），可为 null
     */
    public void writeConnectionToObs(KnowledgeBaseConnectionEntity connection, String connectorType,
        String connectorName, Map<String, String> extraParams) {
        if (connection == null || StringUtils.isEmpty(connection.getId())) {
            log.warn("Connection entity is null or id is empty, skip writing to OBS.");
            return;
        }

        try {
            KnowledgeBaseConnectionEntity effectiveConnection = connection;
            if (extraParams != null && !extraParams.isEmpty()) {
                effectiveConnection = mergeExtraParams(connection, extraParams);
            }

            KbConnectionObsData connectionData = buildConnectionData(effectiveConnection, connectorType, connectorName);
            String jsonContent = JacksonUtils.toJson(connectionData);
            String objectKey = String.format(CONNECTION_PATH, connection.getId());
            mgObsService.uploadObsFile(objectKey, jsonContent, -1);
            log.info("Write connection to OBS success. connectionId: {}, extraParams: {}",
                connection.getId(), extraParams != null ? extraParams.keySet() : "none");
        } catch (Exception e) {
            log.error("Write connection to OBS failed. connectionId: {}", connection.getId(), e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 同步默认知识库连接信息到OBS
     * <p>
     * 应用启动时或刷库后调用，确保默认 LakeSearch 连接的 OBS 文件包含完整信息，
     * 包括 YAML 配置中的 project_id 和 application_id。
     * </p>
     *
     * @param connection 连接实体
     * @param connectorType 连接器类型
     * @param connectorName 连接器名称
     * @param projectId LakeSearch project_id（从 YAML 配置读取）
     * @param applicationId LakeSearch application_id（从 YAML 配置读取）
     */
    public void syncDefaultConnectionToObs(KnowledgeBaseConnectionEntity connection, String connectorType,
        String connectorName, String projectId, String applicationId) {
        Map<String, String> extraParams = new HashMap<>();
        if (StringUtils.isNotEmpty(projectId)) {
            extraParams.put("project_id", projectId);
        }
        if (StringUtils.isNotEmpty(applicationId)) {
            extraParams.put("app_id", applicationId);
        }
        writeConnectionToObs(connection, connectorType, connectorName, extraParams);
    }

    /**
     * 删除OBS上的连接文件
     *
     * @param connectionId 连接ID
     */
    public void deleteConnectionFromObs(String connectionId) {
        if (StringUtils.isEmpty(connectionId)) {
            return;
        }
        try {
            String objectKey = String.format(CONNECTION_PATH, connectionId);
            mgObsService.deleteObsFile(objectKey);
            log.info("Delete connection from OBS success. connectionId: {}", connectionId);
        } catch (Exception e) {
            log.error("Delete connection from OBS failed. connectionId: {}", connectionId, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 为 openjiuwen 知识库写入连接文件到 OBS。
     * <p>
     * openjiuwen 知识库没有 t_knowledge_base_connection 表记录，直接构造连接文件，
     * connectorId 设为 OpenJiuwen，params 中携带 model_config（JSON 字符串），
     * 供 Python 运行时解析 embedding 模型配置。
     * </p>
     *
     * @param connectionId 连接ID（与 kbId 相同）
     * @param kbEntity 知识库实体（含 embeddingModelServiceId / rerankModelServiceId / workspaceId）
     */
    public void writeOpenJiuwenConnectionToObs(String connectionId, KnowledgeBaseEntity kbEntity) {
        if (StringUtils.isEmpty(connectionId) || kbEntity == null) {
            log.warn("connectionId is empty or kbEntity is null, skip writing openjiuwen connection to OBS.");
            return;
        }

        try {
            Map<String, Object> modelConfigMap = new HashMap<>();
            modelConfigMap.put("model_service_id", kbEntity.getEmbeddingModelServiceId());
            modelConfigMap.put("workspace_id", kbEntity.getWorkspaceId());
            modelConfigMap.put("project_id", "0");
            modelConfigMap.put("auth_id", "");
            String modelConfigJson = JacksonUtils.toJson(modelConfigMap);

            List<KbConnectionObsData.KbConnectionParamData> params = new ArrayList<>();
            params.add(KbConnectionObsData.KbConnectionParamData.builder()
                .code("model_config")
                .value(modelConfigJson)
                .build());

            if (StringUtils.isNotEmpty(kbEntity.getRerankModelServiceId())) {
                Map<String, Object> rerankerConfigMap = new HashMap<>();
                rerankerConfigMap.put("model_service_id", kbEntity.getRerankModelServiceId());
                rerankerConfigMap.put("workspace_id", kbEntity.getWorkspaceId());
                rerankerConfigMap.put("project_id", "0");
                rerankerConfigMap.put("auth_id", "");
                String rerankerConfigJson = JacksonUtils.toJson(rerankerConfigMap);
                params.add(KbConnectionObsData.KbConnectionParamData.builder()
                    .code("reranker_config")
                    .value(rerankerConfigJson)
                    .build());
            }

            KbConnectionObsData data = KbConnectionObsData.builder()
                .connectionId(connectionId)
                .connectorId("OpenJiuwen")
                .connectorType("inside")
                .connectorName("OpenJiuwen")
                .knowledgeSource("OpenJiuwen")
                .name("OpenJiuwen")
                .status("OPEN")
                .params(params)
                .build();

            String jsonContent = JacksonUtils.toJson(data);
            String objectKey = String.format(CONNECTION_PATH, connectionId);
            mgObsService.uploadObsFile(objectKey, jsonContent, -1);
            log.info("Write openjiuwen connection to OBS success. connectionId: {}", connectionId);
        } catch (Exception e) {
            log.error("Write openjiuwen connection to OBS failed. connectionId: {}", connectionId, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    // ==================== 知识库文件操作（仅含知识库自身信息 + connectionId 引用） ====================

    /**
     * 将知识库信息写入OBS（仅含知识库自身信息，通过connectionId引用连接文件）
     * <p>
     * 每个知识库一个文件，连接信息存储在独立的连接文件中，消费方需分别读取。
     * </p>
     *
     * @param knowledgeBase 知识库实体
     */
    public void writeKnowledgeBaseToObs(KnowledgeBaseEntity knowledgeBase) {
        if (knowledgeBase == null || StringUtils.isEmpty(knowledgeBase.getId())) {
            log.warn("KnowledgeBase entity is null or id is empty, skip writing to OBS.");
            return;
        }

        try {
            KbKnowledgeBaseObsData kbData = buildKnowledgeBaseData(knowledgeBase);
            String jsonContent = JacksonUtils.toJson(kbData);
            String objectKey = String.format(KNOWLEDGE_BASE_PATH, knowledgeBase.getId());
            mgObsService.uploadObsFile(objectKey, jsonContent, -1);
            log.info("Write knowledge base to OBS success. knowledgeBaseId: {}", knowledgeBase.getId());
        } catch (Exception e) {
            log.error("Write knowledge base to OBS failed. knowledgeBaseId: {}", knowledgeBase.getId(), e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 删除OBS上的知识库文件
     *
     * @param knowledgeBaseId 知识库ID
     */
    public void deleteKnowledgeBaseFromObs(String knowledgeBaseId) {
        if (StringUtils.isEmpty(knowledgeBaseId)) {
            return;
        }
        try {
            String objectKey = String.format(KNOWLEDGE_BASE_PATH, knowledgeBaseId);
            mgObsService.deleteObsFile(objectKey);
            log.info("Delete knowledge base from OBS success. knowledgeBaseId: {}", knowledgeBaseId);
        } catch (Exception e) {
            log.error("Delete knowledge base from OBS failed. knowledgeBaseId: {}", knowledgeBaseId, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    // ==================== 内部方法 ====================

    /**
     * 将额外的配置参数合并到连接实体的 params 列表中
     * <p>
     * 不修改原实体，创建一个新的 params 列表。如果原 params 中已存在同 code 的参数，则用 extraParams 的值覆盖。
     * </p>
     *
     * @param connection 原连接实体
     * @param extraParams 额外参数（key=code, value=value）
     * @return 包含合并后 params 的连接实体副本
     */
    private KnowledgeBaseConnectionEntity mergeExtraParams(KnowledgeBaseConnectionEntity connection,
        Map<String, String> extraParams) {
        // 先将现有 params 转为 map，方便去重
        Map<String, String> paramsMap = new HashMap<>();
        if (CollectionUtils.isNotEmpty(connection.getParams())) {
            for (KnowledgeBaseConnectionParam param : connection.getParams()) {
                paramsMap.put(param.getCode(), param.getValue());
            }
        }
        // 合并额外参数（覆盖同名参数）
        paramsMap.putAll(extraParams);

        // 构建新的 params 列表
        List<KnowledgeBaseConnectionParam> mergedParams = new ArrayList<>();
        for (Map.Entry<String, String> entry : paramsMap.entrySet()) {
            mergedParams.add(new KnowledgeBaseConnectionParam(entry.getKey(), entry.getValue()));
        }

        // 创建实体副本，避免修改原实体
        KnowledgeBaseConnectionEntity copy = new KnowledgeBaseConnectionEntity();
        copy.setId(connection.getId());
        copy.setConnectorId(connection.getConnectorId());
        copy.setConnectorName(connection.getConnectorName());
        copy.setConnectorType(connection.getConnectorType());
        copy.setName(connection.getName());
        copy.setStatus(connection.getStatus());
        copy.setIcon(connection.getIcon());
        copy.setDescription(connection.getDescription());
        copy.setParams(mergedParams);
        copy.setKrb5File(connection.getKrb5File());
        copy.setKeytabFile(connection.getKeytabFile());
        copy.setKnowledgeBaseCapacity(connection.getKnowledgeBaseCapacity());
        copy.setDomainId(connection.getDomainId());
        copy.setUsedAbilities(connection.getUsedAbilities());
        return copy;
    }

    /**
     * 构建连接文件的JSON数据结构
     */
    private KbConnectionObsData buildConnectionData(KnowledgeBaseConnectionEntity connection,
        String connectorType, String connectorName) {
        // params：manager服务在创建/更新连接时已通过checkAndEncryptedParams对SECRET类型参数加密，
        // 写入OBS时直接使用，无需二次加密
        List<KbConnectionObsData.KbConnectionParamData> paramsList = null;
        if (CollectionUtils.isNotEmpty(connection.getParams())) {
            paramsList = connection.getParams().stream()
                .map(param -> KbConnectionObsData.KbConnectionParamData.builder()
                    .code(param.getCode())
                    .value(param.getValue())
                    .build())
                .collect(Collectors.toList());
        }

        return KbConnectionObsData.builder()
            .connectionId(connection.getId())
            .connectorId(connection.getConnectorId())
            .connectorType(connectorType)
            .connectorName(connectorName)
            // 知识源模式标记：Python 端读到 CUSTOM 时走 CUSTOM 检索语义
            .knowledgeSource(knowledgeSource)
            .name(connection.getName())
            .status(connection.getStatus() != null ? connection.getStatus().toString() : null)
            .krb5File(connection.getKrb5File())
            .keytabFile(connection.getKeytabFile())
            .usedAbilities(connection.getUsedAbilities())
            .params(paramsList)
            .build();
    }

    /**
     * 构建知识库文件的JSON数据结构（仅含知识库自身信息 + connectionId 引用）
     */
    private KbKnowledgeBaseObsData buildKnowledgeBaseData(KnowledgeBaseEntity knowledgeBase) {
        return KbKnowledgeBaseObsData.builder()
            .knowledgeBaseId(knowledgeBase.getId())
            .knowledgeBaseName(knowledgeBase.getName())
            .type(knowledgeBase.getType())
            .externalId(knowledgeBase.getExternalId())
            .status(knowledgeBase.getStatus())
            .connectionId(knowledgeBase.getKnowledgeBaseConnectionId())
            .build();
    }
}

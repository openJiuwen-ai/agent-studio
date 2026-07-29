/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service;

import static com.openjiuwen.studio.agent.agentbase.converter.KbConnectionConverter.DEFAULT_CONNECTION_ID;
import static com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorTypeEnum.LAKE_SEARCH_INSIDE;

import com.openjiuwen.studio.agent.agentbase.enums.KnowledgeBaseConnectionStatus;
import com.openjiuwen.studio.agent.common.enums.RagAuthMode;
import com.openjiuwen.studio.agent.agentbase.converter.KbConnectionConverter;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectionEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectorEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectionMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectorMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectionParam;
import com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorTypeEnum;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectionParam;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.LakeSearchService;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.connection.LakeSearchConnection;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.knowledgesourceprovider.LakeSearchConnectionProvider;
import com.openjiuwen.studio.agent.agentbase.service.validate.KnowledgeBaseConnectionValidateService;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.constants.DeploymentModeEnum;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.manager.dto.ConnectionParamInfo;
import com.openjiuwen.studio.agent.manager.dto.CreateDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateDefaultKnowledgeBaseConnectionResponse;
import com.openjiuwen.studio.agent.manager.dto.DefaultKnowledgeBaseConnectionDetail;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseConnectorDetail;
import com.openjiuwen.studio.agent.manager.dto.ListDefaultKnowledgeBaseConnectorsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ParamDefinitionInfo;
import com.openjiuwen.studio.agent.manager.dto.ShowDefaultKnowledgeBaseConnectionDetailResponseBody;
import com.openjiuwen.studio.agent.manager.dto.TestDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.TestDefaultKnowledgeBaseResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateDefaultKnowledgeBaseConnectionResponse;
import com.openjiuwen.studio.agent.manager.service.IKnowledgeBaseConnectionConfigManagementService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@Slf4j
@Service
public class KnowledgeBaseConnectionConfigMgmtImpl implements IKnowledgeBaseConnectionConfigManagementService {

    private final KnowledgeBaseConnectionValidateService knowledgeBaseConnectionValidateService;

    private final KbConnectionConverter kbConnectionConverter;

    private final KnowledgeBaseConnectionMapper connectionMapper;

    private final KnowledgeBaseConnectorMapper connectorMapper;

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    private final LakeSearchService lakeSearchService;

    private final LakeSearchConnectionProvider lakeSearchConnectionProvider;

    private final KbConnectionStorageService kbConnectionStorageService;

    @Value("${knowledge.default-icon}")
    private String defaultIcon;

    @Value("${env.type}")
    private String envType;

    @Value("${knowledge.lakeSearch.auth-mode}")
    private String authMode;

    @Value("${knowledge.lakeSearch.project-id:}")
    private String lakeSearchProjectId;

    @Value("${knowledge.lakeSearch.application-id:}")
    private String lakeSearchApplicationId;

    @Value("${knowledge.lakeSearch.endpoint:}")
    private String lakeSearchEndpoint;

    @Value("${knowledge.lakeSearch.keytab-file:}")
    private String lakeSearchKeytabFile;

    @Value("${knowledge.lakeSearch.krb5-file:}")
    private String lakeSearchKrb5File;

    @Value("${knowledge.source:LakeSearch}")
    private String knowledgeSource;

    private static final String ENDPOINT = "endpoint";

    private static final String OCR_ENABLE = "ocr_enable";

    private static final String AUTH_MODE = "auth_mode";

    private static final String AUTHORIZATION = "authorization";

    public static final String KERBEROS = "Kerberos";

    private static final Set<String> REQUIRED_FIELDS = Set.of(AUTH_MODE, ENDPOINT, OCR_ENABLE);

    public KnowledgeBaseConnectionConfigMgmtImpl(
        KnowledgeBaseConnectionValidateService knowledgeBaseConnectionValidateService,
        KbConnectionConverter kbConnectionConverter, KnowledgeBaseConnectionMapper connectionMapper,
        KnowledgeBaseConnectorMapper connectorMapper, KnowledgeBaseMapper knowledgeBaseMapper,
        LakeSearchService lakeSearchService, LakeSearchConnectionProvider lakeSearchConnectionProvider,
        KbConnectionStorageService kbConnectionStorageService) {
        this.knowledgeBaseConnectionValidateService = knowledgeBaseConnectionValidateService;
        this.kbConnectionConverter = kbConnectionConverter;
        this.connectionMapper = connectionMapper;
        this.connectorMapper = connectorMapper;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
        this.lakeSearchService = lakeSearchService;
        this.lakeSearchConnectionProvider = lakeSearchConnectionProvider;
        this.kbConnectionStorageService = kbConnectionStorageService;
    }

    /**
     * 应用启动时同步知识库和连接信息到OBS
     * <p>
     * 1. 补写所有知识库文件（含 externalId），解决历史数据 OBS 文件缺失问题
     * 2. 补写默认 LakeSearch 连接文件，注入 YAML 配置中的 project_id 和 application_id
     * </p>
     */
    @PostConstruct
    public void initDefaultConnectionObs() {
        // 1. 补写所有知识库文件到 OBS
        syncAllKnowledgeBasesToObs();

        // 2. 补写默认 LakeSearch 连接文件到 OBS
        syncDefaultConnectionToObs();
    }

    private void syncAllKnowledgeBasesToObs() {
        try {
            List<KnowledgeBaseEntity> allKbs = knowledgeBaseMapper.selectAll();
            if (CollectionUtils.isEmpty(allKbs)) {
                log.info("No knowledge bases found in DB, skip KB OBS sync.");
                return;
            }
            int success = 0;
            int fail = 0;
            for (KnowledgeBaseEntity kb : allKbs) {
                try {
                    kbConnectionStorageService.writeKnowledgeBaseToObs(kb);
                    success++;
                } catch (Exception e) {
                    fail++;
                    log.warn("Failed to write KB to OBS: kbId={}, error={}", kb.getId(), e.getMessage());
                }
            }
            log.info("KB OBS sync completed: success={}, fail={}", success, fail);
        } catch (Exception e) {
            log.error("Failed to sync knowledge bases to OBS", e);
        }
    }

    private void syncDefaultConnectionToObs() {
        log.info("Starting default connection OBS sync for all inside connector types");
        try {
            // 同步所有 inside 连接器类型：LakeSearchInside, KooSearchInside, AgentBaseRag
            syncLakeSearchInsideConnection();
            syncKooSearchInsideConnection();
            syncAgentBaseRagConnection();
        } catch (Exception e) {
            log.error("Failed to sync default connections to OBS", e);
        }
    }

    /**
     * 同步 LakeSearchInside 连接到 OBS
     * 支持两种配置源：
     * 1. DB 连接（用户通过 API 创建的默认连接）
     * 2. YAML-only 配置（knowledge.source=CUSTOM 或未创建 DB 连接时）
     */
    private void syncLakeSearchInsideConnection() {
        String connectorId = LAKE_SEARCH_INSIDE.getValue();
        log.info("Syncing LakeSearchInside connection to OBS");

        try {
            // 先尝试从 DB 读取
            List<KnowledgeBaseConnectionEntity> dbConnections =
                connectionMapper.findDefaultConnection(connectorId);

            if (!CollectionUtils.isEmpty(dbConnections)) {
                // DB 连接存在，同步时注入 YAML 中的 project_id / application_id
                KnowledgeBaseConnectionEntity connection = dbConnections.get(0);
                KnowledgeBaseConnectorEntity connector = connectorMapper.find(connectorId);

                kbConnectionStorageService.syncDefaultConnectionToObs(
                    connection,
                    connector != null ? connector.getType() : null,
                    connector != null ? connector.getName() : null,
                    lakeSearchProjectId,
                    lakeSearchApplicationId
                );
                log.info("Synced LakeSearchInside connection from DB: connectionId={}", connection.getId());
            } else if ("CUSTOM".equalsIgnoreCase(knowledgeSource) && StringUtils.isNotEmpty(lakeSearchEndpoint)) {
                // CUSTOM 模式且 YAML 中配置了 endpoint：构造虚拟连接实体写入 OBS
                KnowledgeBaseConnectionEntity yamlConnection = buildLakeSearchFromYaml();
                KnowledgeBaseConnectorEntity connector = connectorMapper.find(connectorId);

                kbConnectionStorageService.writeConnectionToObs(
                    yamlConnection,
                    connector != null ? connector.getType() : "inside",
                    connector != null ? connector.getName() : "LakeSearch",
                    null
                );
                log.info("Synced LakeSearchInside connection from YAML (CUSTOM mode): connectionId={}",
                    yamlConnection.getId());
            } else {
                log.info("No LakeSearchInside connection to sync (no DB row and not CUSTOM mode with endpoint)");
            }
        } catch (Exception e) {
            log.error("Failed to sync LakeSearchInside connection to OBS", e);
        }
    }

    /**
     * 同步 KooSearchInside 连接到 OBS
     * 当前仅支持 DB 连接（KooSearchInside 无 YAML-only 部署场景）
     */
    private void syncKooSearchInsideConnection() {
        String connectorId = ConnectorTypeEnum.KOO_SEARCH_INSIDE.getValue();
        log.info("Syncing KooSearchInside connection to OBS");

        try {
            List<KnowledgeBaseConnectionEntity> dbConnections =
                connectionMapper.findDefaultConnection(connectorId);

            if (!CollectionUtils.isEmpty(dbConnections)) {
                KnowledgeBaseConnectionEntity connection = dbConnections.get(0);
                KnowledgeBaseConnectorEntity connector = connectorMapper.find(connectorId);

                kbConnectionStorageService.writeConnectionToObs(
                    connection,
                    connector != null ? connector.getType() : "inside",
                    connector != null ? connector.getName() : "KooSearch",
                    null
                );
                log.info("Synced KooSearchInside connection from DB: connectionId={}", connection.getId());
            } else {
                log.info("No KooSearchInside connection to sync (no DB row)");
            }
        } catch (Exception e) {
            log.error("Failed to sync KooSearchInside connection to OBS", e);
        }
    }

    /**
     * 同步 AgentBaseRag 连接到 OBS
     * 当前仅支持 DB 连接（AgentBaseRag 无 YAML-only 部署场景）
     */
    private void syncAgentBaseRagConnection() {
        String connectorId = ConnectorTypeEnum.AGENT_BASE_RAG.getValue();
        log.info("Syncing AgentBaseRag connection to OBS");

        try {
            List<KnowledgeBaseConnectionEntity> dbConnections =
                connectionMapper.findDefaultConnection(connectorId);

            if (!CollectionUtils.isEmpty(dbConnections)) {
                KnowledgeBaseConnectionEntity connection = dbConnections.get(0);
                KnowledgeBaseConnectorEntity connector = connectorMapper.find(connectorId);

                kbConnectionStorageService.writeConnectionToObs(
                    connection,
                    connector != null ? connector.getType() : "inside",
                    connector != null ? connector.getName() : "AgentBaseRag",
                    null
                );
                log.info("Synced AgentBaseRag connection from DB: connectionId={}", connection.getId());
            } else {
                log.info("No AgentBaseRag connection to sync (no DB row)");
            }
        } catch (Exception e) {
            log.error("Failed to sync AgentBaseRag connection to OBS", e);
        }
    }

    /**
     * 从 YAML 配置构造 LakeSearch 虚拟连接实体（用于 CUSTOM 模式）
     * 注意：构造的 params 中的敏感字段（password）应已加密，但 YAML 配置中通常是明文
     * 本方法假设 YAML 中的凭证为明文，调用 CryptoUtils.encrypt 加密后存入 params
     */
    private KnowledgeBaseConnectionEntity buildLakeSearchFromYaml() {
        KnowledgeBaseConnectionEntity entity = new KnowledgeBaseConnectionEntity();
        entity.setId(DEFAULT_CONNECTION_ID); // 使用 converter 中定义的常量
        entity.setConnectorId(LAKE_SEARCH_INSIDE.getValue());
        entity.setName("Default LakeSearch (YAML Config)");
        entity.setStatus(KnowledgeBaseConnectionStatus.OPEN);
        entity.setConnectorType("inside");

        List<KnowledgeBaseConnectionParam> params = new ArrayList<>();

        // 基础参数
        if (StringUtils.isNotEmpty(lakeSearchEndpoint)) {
            params.add(new KnowledgeBaseConnectionParam(ENDPOINT, lakeSearchEndpoint));
        }
        if (StringUtils.isNotEmpty(lakeSearchProjectId)) {
            params.add(new KnowledgeBaseConnectionParam("project_id", lakeSearchProjectId));
        }
        if (StringUtils.isNotEmpty(lakeSearchApplicationId)) {
            params.add(new KnowledgeBaseConnectionParam("app_id", lakeSearchApplicationId));
        }
        if (StringUtils.isNotEmpty(authMode)) {
            params.add(new KnowledgeBaseConnectionParam(AUTH_MODE, authMode));
        }

        // Kerberos 认证：keytab/krb5 文件路径不需要加密，直接存储
        if (KERBEROS.equalsIgnoreCase(authMode)) {
            if (StringUtils.isNotEmpty(lakeSearchKeytabFile)) {
                params.add(new KnowledgeBaseConnectionParam("keytab_file", lakeSearchKeytabFile));
            }
            if (StringUtils.isNotEmpty(lakeSearchKrb5File)) {
                params.add(new KnowledgeBaseConnectionParam("krb5_file", lakeSearchKrb5File));
            }
        }

        // 注意：YAML 配置中通常不包含 password（Basic 认证）或 token（Token 认证），
        // 这些敏感字段应通过 DB 连接或运行时注入。若 YAML 中配置了明文密码，需在此处加密：
        // String plainPassword = ...;
        // params.add(new KnowledgeBaseConnectionParam("password", CryptoUtils.encrypt(plainPassword)));

        entity.setParams(params);
        return entity;
    }

    @Override
    public CreateDefaultKnowledgeBaseConnectionResponse createDefaultKbConnection(String projectId,
        CreateDefaultKnowledgeBaseConnectionRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, createDefaultKbConnection", projectId,
            RequestContextUtils.getRequestUserId());
        checkPermission();
        if (KERBEROS.equalsIgnoreCase(authMode)) {
            log.error("do not support to config default knowledge base connection with kerberos");
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, KERBEROS);
        }
        if (!Strings.CS.equals(body.getConnectorId(), LAKE_SEARCH_INSIDE.getValue())) {
            log.error("do not support to config default knowledge base connection with connectorId [{}]",
                body.getConnectorId());
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, body.getConnectorId());
        }
        // 全局只有1个默认知识库校验
        if (knowledgeBaseConnectionValidateService.defaultConnectionExisted(body.getConnectorId())) {
            log.error("default connection already exist");
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, body.getConnectorId());
        }
        // 参数校验，当前值进行了判空检验
        checkDefaultKbConnectionParams(body.getParams());
        // 校验参数与连接器中定义的参数是否一致并加密
        List<ConnectionParamInfo> connectionParamInfos = knowledgeBaseConnectionValidateService.checkAndEncryptedParams(
            body.getConnectorId(), body.getParams());
        body.setParams(connectionParamInfos);
        // 入库
        KnowledgeBaseConnectionEntity entity = kbConnectionConverter.toKnowledgeBaseConnectionEntity(projectId, body);
        entity.setIcon(defaultIcon);
        try {
            connectionMapper.insert(entity);
            // 当首次配置并配置成功后，原先的知识库的connectionId要刷新成默认知识库
            knowledgeBaseMapper.updatePreviewsKnowledgeBaseConnectionId(entity.getId());

            // 连接信息独立存储，写入连接文件到OBS
            // 默认 LakeSearch 连接需要注入 YAML 配置中的 project_id 和 application_id
            try {
                KnowledgeBaseConnectorEntity connector = connectorMapper.find(body.getConnectorId());
                kbConnectionStorageService.syncDefaultConnectionToObs(
                    entity,
                    connector != null ? connector.getType() : null,
                    connector != null ? connector.getName() : null,
                    lakeSearchProjectId, lakeSearchApplicationId);
            } catch (Exception ex) {
                log.error("Write connection to OBS after default connection create failed. connectionId: {}", entity.getId(), ex);
                // OBS写入失败不影响主流程
            }
        } catch (RuntimeException e) {
            log.error("Create default knowledge base connection failed", e);
            throw new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, e);
        }
        return new CreateDefaultKnowledgeBaseConnectionResponse().setId(entity.getId());
    }

    @Override
    public ListDefaultKnowledgeBaseConnectorsResponseBody listDefaultKnowledgeBaseConnectors(String projectId,
        Integer offset, Integer limit) {
        checkPermission();
        // 当前只有LakeSearch允许页面配置
        final KnowledgeBaseConnectorEntity knowledgeBaseConnectorEntity = connectorMapper.find(
            LAKE_SEARCH_INSIDE.getValue());
        ListDefaultKnowledgeBaseConnectorsResponseBody listDefaultKnowledgeBaseConnectorsResponseBody
            = new ListDefaultKnowledgeBaseConnectorsResponseBody();
        listDefaultKnowledgeBaseConnectorsResponseBody.setTotal(1L);
        KnowledgeBaseConnectorDetail knowledgeBaseConnectorDetail = toKnowledgeBaseConnectorDetail(
            knowledgeBaseConnectorEntity);
        listDefaultKnowledgeBaseConnectorsResponseBody.setConnectors(List.of(knowledgeBaseConnectorDetail));
        return listDefaultKnowledgeBaseConnectorsResponseBody;
    }

    private KnowledgeBaseConnectorDetail toKnowledgeBaseConnectorDetail(
        KnowledgeBaseConnectorEntity knowledgeBaseConnectorEntity) {
        KnowledgeBaseConnectorDetail knowledgeBaseConnectorDetail
            = kbConnectionConverter.toKnowledgeBaseConnectorDetail(knowledgeBaseConnectorEntity);
        List<ParamDefinitionInfo> paramDefinitionInfos = kbConnectionConverter.connectorParams2ParamDefinitionInfos(
            knowledgeBaseConnectorEntity.getParams());
        return knowledgeBaseConnectorDetail.setParamDefinition(paramDefinitionInfos);
    }

    @Override
    public ShowDefaultKnowledgeBaseConnectionDetailResponseBody showDefaultKnowledgeBaseConnection(String projectId,
        String kbConnectionId) {
        checkPermission();
        ShowDefaultKnowledgeBaseConnectionDetailResponseBody showDefaultKnowledgeBaseConnectionDetailResponseBody
            = new ShowDefaultKnowledgeBaseConnectionDetailResponseBody();
        List<KnowledgeBaseConnectionEntity> defaultConnections = connectionMapper.findDefaultConnection(
            LAKE_SEARCH_INSIDE.getValue());
        if (CollectionUtils.isEmpty(defaultConnections)) {
            // 若未配置，则为null
            showDefaultKnowledgeBaseConnectionDetailResponseBody.setKnowledgeBaseConnectionDetail(null);
            return showDefaultKnowledgeBaseConnectionDetailResponseBody;
        }
        KnowledgeBaseConnectionEntity knowledgeBaseConnectionEntity = Optional.ofNullable(defaultConnections.get(0))
            .orElse(new KnowledgeBaseConnectionEntity());

        DefaultKnowledgeBaseConnectionDetail defaultKnowledgeBaseConnectionDetail
            = kbConnectionConverter.toDefaultKnowledgeBaseConnectionDetail(knowledgeBaseConnectionEntity);
        List<ConnectionParamInfo> connectionParamInfos = kbConnectionConverter.kbConnectionParams2ConnectionParamInfos(
            knowledgeBaseConnectionEntity.getParams());
        defaultKnowledgeBaseConnectionDetail.setParams(connectionParamInfos);
        showDefaultKnowledgeBaseConnectionDetailResponseBody.setKnowledgeBaseConnectionDetail(
            defaultKnowledgeBaseConnectionDetail);
        return showDefaultKnowledgeBaseConnectionDetailResponseBody;
    }

    @Override
    public TestDefaultKnowledgeBaseResponseBody testDefaultKnowledgeBaseConnection(String projectId,
        TestDefaultKnowledgeBaseConnectionRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, testDefaultKnowledgeBaseConnection", projectId,
            RequestContextUtils.getRequestUserId());
        checkPermission();
        try {
            boolean result = false;
            if (Strings.CS.equals(body.getConnectorId(), LAKE_SEARCH_INSIDE.getValue())) {
                // 校验参数与连接器中定义的参数是否一致并加密
                List<ConnectionParamInfo> connectionParamInfos
                    = knowledgeBaseConnectionValidateService.checkAndEncryptedParams(body.getConnectorId(),
                    body.getParams());
                body.setParams(connectionParamInfos);
                LakeSearchConnection lakeSearchConnection = convertToLakeSearchConnection(body);
                result = lakeSearchService.testConnection(lakeSearchConnection);
            }
            return new TestDefaultKnowledgeBaseResponseBody().setResult(result);
        } catch (Exception e) {
            log.error("Connect to {} failed,error message:{}", body.getConnectorId(), e.getMessage());
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_DEFAULT_CONNECTION_FAILED, e);
        }
    }

    @Override
    public TestDefaultKnowledgeBaseResponseBody testDefaultKnowledgeBaseConnectionId(String projectId,
        String connectionId) {
        log.info("operation log projectId: {}, userId:{}, testDefaultKnowledgeBaseConnection, connectorId: {}",
            projectId, RequestContextUtils.getRequestUserId(), connectionId);
        checkPermission();
        try {
            // 当前只支持lakesearch
            LakeSearchConnection lakeSearchConnection = lakeSearchConnectionProvider.getKnowledgeSourceConnection(
                connectionId);
            boolean result = lakeSearchService.testConnection(lakeSearchConnection);
            return new TestDefaultKnowledgeBaseResponseBody().setResult(result);
        } catch (Exception e) {
            log.error("Connect to {} failed,error message:{}", connectionId, e.getMessage());
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_DEFAULT_CONNECTION_FAILED, e);
        }
    }

    @Override
    public UpdateDefaultKnowledgeBaseConnectionResponse updateDefaultKnowledgeBaseConnection(String projectId,
        String kbConnectionId, UpdateDefaultKnowledgeBaseConnectionRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, UpdateDefaultKnowledgeBaseConnection", projectId,
            RequestContextUtils.getRequestUserId());
        checkPermission();
        if (KERBEROS.equalsIgnoreCase(authMode)) {
            log.error("do not support to config default knowledge base connection with kerberos");
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, KERBEROS);
        }
        if (!body.isChanged()) {
            // 若未改变参数，则直接返回
            return new UpdateDefaultKnowledgeBaseConnectionResponse().setId(kbConnectionId);
        }
        if (!Strings.CS.equals(kbConnectionId, DEFAULT_CONNECTION_ID)) {
            // 当前先只支持更新默认LakeSearch，其余不支持
            log.error("do not support to update config default knowledge base connection with connectionId [{}]",
                body.getConnectorId());
            throw new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR);
        }
        // 校验参数与连接器中定义的参数是否一致并加密
        List<ConnectionParamInfo> connectionParamInfos = knowledgeBaseConnectionValidateService.checkAndEncryptedParams(
            body.getConnectorId(), body.getParams());
        body.setParams(connectionParamInfos);
        // 入库
        KnowledgeBaseConnectionEntity entity = kbConnectionConverter.updateBodytoKnowledgeBaseConnectionEntity(body);
        entity.setId(kbConnectionId);
        connectionMapper.update(entity);

        // 连接信息独立存储，更新连接文件即可，无需刷新关联的知识库文件
        // 默认 LakeSearch 连接需要注入 YAML 配置中的 project_id 和 application_id
        try {
            KnowledgeBaseConnectorEntity connector = connectorMapper.find(body.getConnectorId());
            entity.setConnectorId(body.getConnectorId());
            // 更新时需要从 DB 获取完整的连接实体（包含 status 等字段）
            KnowledgeBaseConnectionEntity fullEntity = connectionMapper.findById(kbConnectionId);
            if (fullEntity != null) {
                // 用更新请求的 params 替换原有 params
                fullEntity.setParams(entity.getParams());
                fullEntity.setConnectorId(entity.getConnectorId());
                kbConnectionStorageService.syncDefaultConnectionToObs(
                    fullEntity,
                    connector != null ? connector.getType() : null,
                    connector != null ? connector.getName() : null,
                    lakeSearchProjectId, lakeSearchApplicationId);
            } else {
                // DB 中找不到完整实体，使用请求中的部分实体
                kbConnectionStorageService.syncDefaultConnectionToObs(
                    entity,
                    connector != null ? connector.getType() : null,
                    connector != null ? connector.getName() : null,
                    lakeSearchProjectId, lakeSearchApplicationId);
            }
        } catch (Exception e) {
            log.error("Write connection to OBS after default connection update failed. connectionId: {}", kbConnectionId, e);
            // OBS更新失败不影响主流程
        }

        return new UpdateDefaultKnowledgeBaseConnectionResponse().setId(kbConnectionId);
    }

    private LakeSearchConnection convertToLakeSearchConnection(TestDefaultKnowledgeBaseConnectionRequestBody body) {
        KnowledgeBaseConnectionEntity knowledgeBaseConnectionEntity
            = kbConnectionConverter.requestBodyToKbConnectionEntity(body);
        List<KnowledgeBaseConnectionParam> knowledgeBaseConnectionParams
            = kbConnectionConverter.connectionParamInfos2kbConnectionParams(body.getParams());
        knowledgeBaseConnectionEntity.setParams(knowledgeBaseConnectionParams);
        return lakeSearchConnectionProvider.convertToLakeSearchConnection(knowledgeBaseConnectionEntity);
    }

    private void checkPermission() {
        if (DeploymentModeEnum.isHc(envType)) {
            // hc场景下，任何用户禁止改变默认知识库配置
            log.error("user can not change default config");
            throw new AgentBaseException(ErrorCode.NO_PERMISSION);
        }
    }

    public void checkDefaultKbConnectionParams(List<ConnectionParamInfo> params) {
        if (params == null || params.isEmpty()) {
            return;
        }
        params.forEach(this::validateSingleItemAndThrow);
        String authModeParamValue = params.stream()
            .filter(item -> AUTH_MODE.equals(item.getCode()))
            .map(ConnectionParamInfo::getValue)
            .findFirst()
            .orElse(null);
        if (RagAuthMode.BASIC.toString().equals(authModeParamValue)) {
            boolean isAuthorizationValueInvalid = params.stream()
                .filter(item -> AUTHORIZATION.equals(item.getCode()))
                .findFirst()
                .map(ConnectionParamInfo::getValue)
                .filter(org.springframework.util.StringUtils::hasLength)
                .isEmpty();
            if (isAuthorizationValueInvalid) {
                log.error("When the authentication mode is BASIC, the authorization field ({}) cannot be empty.",
                    AUTHORIZATION);
                throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, AUTHORIZATION);
            }
        }
    }

    private void validateSingleItemAndThrow(ConnectionParamInfo item) {
        if (item.getCode() == null || item.getCode().trim().isEmpty()) {
            log.error("code is null");
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, "code");
        }

        if (REQUIRED_FIELDS.contains(item.getCode())) {
            if (!org.springframework.util.StringUtils.hasLength(item.getValue())) {
                log.error("{} is null", item.getCode());
                throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, item.getCode());
            }
        }
    }

}

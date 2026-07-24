/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service;

import static com.openjiuwen.studio.agent.agentbase.common.constant.KooSearchRepoType.EXCLUSIVE;
import static com.openjiuwen.studio.agent.agentbase.common.constant.KooSearchRepoType.SHARE;
import static com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeConnectionRouterService.NO_CONNECTOR;
import static com.openjiuwen.studio.common.service.constant.CommonConstant.TenantType.TENANT_TYPE_2C;
import static java.util.Comparator.comparing;
import static java.util.stream.Collectors.collectingAndThen;
import static java.util.stream.Collectors.toCollection;

import com.fasterxml.jackson.core.type.TypeReference;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.github.pagehelper.PageRowBounds;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.agentbase.common.enums.KnowledgeBaseType;
import com.openjiuwen.studio.agent.agentbase.common.enums.KnowledgeConnectionStatus;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeRepoStatus;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnection;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectionEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseConnectorEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseObsConfigEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeShareScopeEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeTestEntity;
import com.openjiuwen.studio.agent.agentbase.enums.RepoTypeEnum;
import com.openjiuwen.studio.agent.agentbase.enums.ResourceType;
import com.openjiuwen.studio.agent.agentbase.enums.ShareScopeEnum;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectionMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseConnectorMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseObsConfigMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseObsExecuteRecordMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeRepoMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeShareScopeMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeTestMapper;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeRepoInfo;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeBaseConnectorParam;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeRepo;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeRepoInfo;
import com.openjiuwen.studio.agent.agentbase.model.ListKnowledgeBaseParamsForCustom;
import com.openjiuwen.studio.agent.agentbase.model.ListKnowledgeRepoResp;
import com.openjiuwen.studio.agent.agentbase.model.ModelSearchCriteria;
import com.openjiuwen.studio.agent.agentbase.model.SearchTextResp;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeConnectionRouterService;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeRepoContext;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.multiRetriveMerigingStrategy.RetrieveMergingStrategyContext;
import com.openjiuwen.studio.agent.agentbase.service.resource.ResourceUsageFactory;
import com.openjiuwen.studio.agent.agentbase.service.validate.ResourceValidateService;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.knowledge.ChunkUtils;
import com.openjiuwen.studio.agent.agentbase.utils.IconValidator;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.foundation.base.utils.JacksonUtils;
import com.openjiuwen.studio.agent.agentbase.utils.ShareScopeValidUtil;
import com.openjiuwen.studio.agent.agentbase.utils.TenantTypeUtil;
import com.openjiuwen.studio.agent.foundation.base.utils.UUIDGenerator;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SqlLikeEscapeHelper;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.foundation.connection.ConnectionParamType;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorDefinition;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorParamDefinition;
import com.openjiuwen.studio.agent.foundation.connection.KnowledgeBaseConnectorContext;
import com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorParamConstants;
import com.openjiuwen.studio.agent.foundation.connection.constants.QueryModeEnum;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalKnowledgeBaseInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalRetrieveResultInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.KnowledgeBaseTagInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.agent.foundation.connection.model.KnowledgeBaseRetrieval;
import com.openjiuwen.studio.agent.foundation.connection.model.RetrieveKnowledgeBaseReq;
import com.openjiuwen.studio.agent.foundation.connection.utils.AgentBaseListUtil;
import com.openjiuwen.studio.agent.foundation.connection.utils.ConnectorParamUtil;
import com.openjiuwen.studio.agent.manager.dto.ChatReferenceInfo;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateExternalKnowledgeBaseRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateExternalKnowledgeBaseResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateExternalKnowledgeResult;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.DeleteOneResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ExternalKnowledgeBaseSource;
import com.openjiuwen.studio.agent.manager.dto.ExternalKnowledgeItem;
import com.openjiuwen.studio.agent.manager.dto.FileInfo;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRepoMetadata;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSearchRecord;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSearchRecordRsp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeTagInfo;
import com.openjiuwen.studio.agent.manager.dto.ListExternalKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListExternalKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeModelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeModelsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeRepoReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeRepoTagsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeSearchRecordsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTagsResp;
import com.openjiuwen.studio.agent.manager.dto.ModelConf;
import com.openjiuwen.studio.agent.manager.dto.ModelInfo;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.common.dto.knowledge.ParseConf;
import com.openjiuwen.studio.agent.manager.dto.PermissionsRequestBody;
import com.openjiuwen.studio.agent.manager.dto.RagChunkParserConf;
import com.openjiuwen.studio.agent.manager.dto.SearchKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.SearchKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.common.dto.knowledge.SplitConf;
import com.openjiuwen.studio.agent.manager.dto.StartKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.StopKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateKnowledgeVisibilityResponse;
import com.openjiuwen.studio.agent.manager.service.IKnowledgeRepoManagementService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 功能描述
 *
 * @since 2025-08-12
 */
@Slf4j
@Service
public class KnowledgeBaseServiceImpl implements IKnowledgeRepoManagementService {

    public final static String NORMAL_MODEL_STATUS = "ready";

    public final static String MY_SHARED = "my_shared";

    public final static String OTHER_SHARED = "other_shared";

    private final KnowledgeRepoMapper knowledgeRepoMapper;

    private final KnowledgeTestMapper knowledgeTestMapper;

    private final KnowledgeRepoContext knowledgeRepoContext;

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    private final KnowledgeBaseConnectorContext knowledgeBaseConnectorContext;

    private final KnowledgeBaseConnectorMapper knowledgeBaseConnectorMapper;

    private final KnowledgeBaseConnectionMapper knowledgeBaseConnectionMapper;

    private final KnowledgeBaseObsConfigMapper knowledgeBaseObsConfigMapper;

    private final KnowledgeBaseObsExecuteRecordMapper knowledgeBaseObsExecuteRecordMapper;

    private final KnowledgeShareScopeMapper knowledgeShareScopeMapper;

    private final ResourceValidateService resourceValidateService;

    private final KnowledgeBaseTransactionService knowledgeBaseTransactionService;

    private final RetrieveMergingStrategyContext retrieveMergingStrategyContext;

    private final ResourceUsageFactory resourceUsageFactory;

    private final RedisClient redisClient;

    private final KnowledgeConnectionRouterService knowledgeConnectionRouterService;

    private final KbConnectionStorageService kbConnectionStorageService;

    @Value("${knowledge.bound.limit}")
    private int agentKnowledgeBoundLimit;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${knowledge.icon}")
    private String knowledgeDefaultIcon;

    @Value("${knowledge.kooSearch.embedding-model}")
    private String kosEmbeddingModel;

    @Value("${knowledge.default-icon}")
    private String defaultIcon;

    @Value("${knowledge.icon-max-size:200}")
    private long iconMaxSize;

    @Value("${knowledge.icon-type:png,jpg,jpeg,gif}")
    private String iconType;

    @Value("${knowledge.kooSearch.reRank-model}")
    private String kosReRankModel;

    @Value("${knowledge.lakeSearch.embedding-model}")
    private String mrsEmbeddingModel;

    @Value("${knowledge.lakeSearch.reRank-model}")
    private String mrsReRankModel;

    @Value("${knowledge.repo-share.enable}")
    private boolean logicKnowledgeRepoEnabled;

    /**
     * 图片在 Redis 中的缓存过期时间（单位：天）
     */
    @Value("${knowledge.retrieval-image-validity-days:7}")
    private int retrievalValidityDays;

    @Value("${knowledge.lakeSearch.project-id:}")
    private String lakeSearchProjectId;

    @Value("${knowledge.lakeSearch.application-id:}")
    private String lakeSearchApplicationId;

    public KnowledgeBaseServiceImpl(KnowledgeTestMapper knowledgeTestMapper, KnowledgeRepoMapper knowledgeRepoMapper,
        KnowledgeRepoContext knowledgeRepoContext, KnowledgeBaseMapper knowledgeBaseMapper,
        KnowledgeBaseConnectorContext knowledgeBaseConnectorContext,
        KnowledgeBaseConnectorMapper knowledgeBaseConnectorMapper,
        KnowledgeBaseConnectionMapper knowledgeBaseConnectionMapper,
        KnowledgeBaseObsConfigMapper knowledgeBaseObsConfigMapper,
        KnowledgeBaseObsExecuteRecordMapper knowledgeBaseObsExecuteRecordMapper,
        KnowledgeShareScopeMapper knowledgeShareScopeMapper, ResourceValidateService resourceValidateService,
        KnowledgeBaseTransactionService knowledgeBaseTransactionService,
        RetrieveMergingStrategyContext retrieveMergingStrategyContext, ResourceUsageFactory resourceUsageFactory,
        KnowledgeConnectionRouterService knowledgeConnectionRouterService, RedisClient redisClient,
        KbConnectionStorageService kbConnectionStorageService) {
        this.knowledgeTestMapper = knowledgeTestMapper;
        this.knowledgeRepoMapper = knowledgeRepoMapper;
        this.knowledgeRepoContext = knowledgeRepoContext;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
        this.knowledgeBaseConnectorContext = knowledgeBaseConnectorContext;
        this.knowledgeBaseConnectorMapper = knowledgeBaseConnectorMapper;
        this.knowledgeBaseConnectionMapper = knowledgeBaseConnectionMapper;
        this.knowledgeBaseObsConfigMapper = knowledgeBaseObsConfigMapper;
        this.knowledgeBaseObsExecuteRecordMapper = knowledgeBaseObsExecuteRecordMapper;
        this.knowledgeShareScopeMapper = knowledgeShareScopeMapper;
        this.resourceValidateService = resourceValidateService;
        this.knowledgeBaseTransactionService = knowledgeBaseTransactionService;
        this.retrieveMergingStrategyContext = retrieveMergingStrategyContext;
        this.resourceUsageFactory = resourceUsageFactory;
        this.knowledgeConnectionRouterService = knowledgeConnectionRouterService;
        this.redisClient = redisClient;
        this.kbConnectionStorageService = kbConnectionStorageService;
    }


    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "KnowledgeBase",
        description = "接入第三方知识库",
        resourceId = "-1",
        resourceName = "body.knowledgeBaseConnectionId"
    )
    public CreateExternalKnowledgeBaseResponseBody createExternalKnowledgeBase(String projectId, String workspaceId,
        CreateExternalKnowledgeBaseRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, createExternalKnowledgeBase", projectId,
            RequestContextUtils.getRequestUserId());
        resourceValidateService.resourceQuotaCheck(RequestContextUtils.getRequestUserDomainId(),
            ResourceType.THIRD_PARTY_KNOWLEDGE_BASE, body.getKnowledgeBaseExternalIds().size());
        List<CreateExternalKnowledgeResult> response = new ArrayList<>();
        // 对于已经接入到本空间中的第三方知识库，不支持再接入一次
        List<KnowledgeBaseEntity> knowledgeBases = knowledgeBaseMapper.batchQueryKnowledgeBases(projectId, workspaceId,
            null, body.getKnowledgeBaseExternalIds(), null);
        // 注意一个特殊场景，internal类型的知识库是对接的KooSearch/LakeSearch，但是接入第三方知识库时也可能接入的是同一个KooSearch/LakeSearch集群，所以校验外部ID时，整个空间内的知识库都需要校验，而不是只校验某个知识源下的三方知识库
        Set<String> existsExternalId = knowledgeBases.stream()
            .map(KnowledgeBaseEntity::getExternalId)
            .collect(Collectors.toSet());

        // 查询三方知识库系统中所有的知识库
        List<KnowledgeBaseConnection> connections = knowledgeBaseConnectionMapper.batchQueryKnowledgeBaseConnections(
            Lists.newArrayList(body.getKnowledgeBaseConnectionId()), null);
        if (CollectionUtils.isEmpty(connections)) {
            log.error("knowledgeBase connection  {} are not exist.", body.getKnowledgeBaseConnectionId());
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_CONNECTION_NOT_EXIST,
                body.getKnowledgeBaseConnectionId());
        }
        KnowledgeBaseConnectorEntity connector = knowledgeBaseConnectorMapper.find(connections.get(0).getConnectorId());
        ConnectorDefinition connectorDefinition = convertConnectionToDefinition(connections.get(0));
        Map<String, KnowledgeBaseConnectorParam> paramMap = connector.getParams()
            .stream()
            .collect(Collectors.toMap(KnowledgeBaseConnectorParam::getCode, item -> item));
        connectorDefinition.getParamDefinitions().forEach(param -> {
            if (paramMap.containsKey(param.getCode())) {
                param.setType(ConnectionParamType.valueOf(paramMap.get(param.getCode()).getType().toString()));
            }
        });
        List<ExternalKnowledgeBaseInfo> externalKnowledgeBaseInfos = queryAllExternalKnowledgeBases(
            connectorDefinition);
        Map<String, ExternalKnowledgeBaseInfo> externalKbMap = ObjectUtils.firstNonNull(externalKnowledgeBaseInfos,
                Collections.<ExternalKnowledgeBaseInfo>emptyList())
            .stream()
            .collect(Collectors.toMap(ExternalKnowledgeBaseInfo::getKnowledgeBaseId, item -> item));

        List<KnowledgeBaseEntity> externalKnowledgeBaseToCreate = new ArrayList<>();
        body.getKnowledgeBaseExternalIds().forEach(item -> {
            if (existsExternalId.contains(item)) {
                CreateExternalKnowledgeResult failed = new CreateExternalKnowledgeResult();
                failed.setKnowledgeBaseExternalId(item);
                failed.setResult(false);
                failed.setErrorMsg("External knowledge base exists.");
                response.add(failed);
            } else {
                if (!externalKbMap.containsKey(item)) {
                    CreateExternalKnowledgeResult failed = new CreateExternalKnowledgeResult();
                    failed.setKnowledgeBaseExternalId(item);
                    failed.setResult(false);
                    failed.setErrorMsg("External knowledge base not exists in external system.");
                    response.add(failed);
                } else {
                    KnowledgeBaseEntity knowledgeBase = KnowledgeBaseEntity.builder()
                        .id(UUIDGenerator.getUUID())
                        // 补充外部知识库的名称和描述
                        .name(externalKbMap.get(item).getKnowledgeBaseName())
                        .description(externalKbMap.get(item).getDescription())
                        .icon(defaultIcon)
                        .type(KnowledgeBaseType.EXTERNAL.getValue())
                        .knowledgeBaseConnectionId(body.getKnowledgeBaseConnectionId())
                        .externalId(item)
                        .shareScope(ShareScopeEnum.SELF.name())
                        .projectId(projectId)
                        .domainId(RequestContextUtils.getRequestUserDomainId())
                        .domainName(RequestContextUtils.getRequestUserDomainName())
                        .createdUserId(RequestContextUtils.getRequestUserId())
                        .createdUserName(RequestContextUtils.getRequestUserName())
                        .lastUpdateUserId(RequestContextUtils.getRequestUserId())
                        .lastUpdateUserName(RequestContextUtils.getRequestUserName())
                        .createTime(System.currentTimeMillis())
                        .updateTime(System.currentTimeMillis())
                        .workspaceId(workspaceId)
                        .build();
                    externalKnowledgeBaseToCreate.add(knowledgeBase);
                    CreateExternalKnowledgeResult success = new CreateExternalKnowledgeResult();
                    success.setKnowledgeBaseId(knowledgeBase.getId());
                    success.setKnowledgeBaseExternalId(item);
                    success.setResult(true);
                    response.add(success);
                }
            }
        });
        if (CollectionUtils.isNotEmpty(externalKnowledgeBaseToCreate)) {
            knowledgeBaseMapper.batchInsertKnowledgeBase(externalKnowledgeBaseToCreate);
            knowledgeBaseConnectionMapper.updateKnowledgeBaseConnectionStatus(body.getKnowledgeBaseConnectionId(),
                KnowledgeConnectionStatus.OPEN.toString());

            // 将知识库信息（含连接信息）写入OBS
            for (KnowledgeBaseEntity kbEntity : externalKnowledgeBaseToCreate) {
                writeKbWithConnectionToObs(kbEntity);
            }
        }
        return new CreateExternalKnowledgeBaseResponseBody().setKnowledgeBaseResults(response);
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "KnowledgeBase",
        description = "创建知识库",
        resourceId = "-1",
        resourceName = "body.displayName"
    )
    public CreateKnowledgeRepoResponseBody createKnowledgeRepo(String projectId, String workspaceId,
        CreateKnowledgeRepoRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, createKnowledgeBase", projectId,
            RequestContextUtils.getRequestUserId());
        log.info("Thread name", Thread.currentThread().getName());
        KnowledgeRepoEntity knowledgeRepoEntity = toKnowledgeRepoEntity(projectId, body);
        KnowledgeBaseEntity knowledgeBaseEntity = toKnowledgeBaseEntity(knowledgeRepoEntity, workspaceId);
        try {
            knowledgeBaseTransactionService.createKnowledgeBaseInTransaction(knowledgeRepoEntity, knowledgeBaseEntity);
            String externalId = "";
            String source = knowledgeRepoEntity.getSource();
            create(projectId, body, source, externalId, knowledgeBaseEntity, knowledgeRepoEntity);
            return new CreateKnowledgeRepoResponseBody().setKnowledgeRepoId(knowledgeRepoEntity.getKnowledgeRepoId());
        } catch (AgentBaseException ex) {
            log.error("create knowledge base failed", ex);
            rollbackWhenCreateFailed(knowledgeRepoEntity, knowledgeBaseEntity);
            throw ex;
        } catch (RuntimeException ex) {
            log.error("create knowledge base failed", ex);
            rollbackWhenCreateFailed(knowledgeRepoEntity, knowledgeBaseEntity);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_CREATE_FAILED);
        }
    }

    private void rollbackWhenCreateFailed(KnowledgeRepoEntity knowledgeRepoEntity,
        KnowledgeBaseEntity knowledgeBaseEntity) {
        knowledgeBaseTransactionService.clearWhenCreateFailed(RequestContextUtils.getRequestUserDomainId(),
            knowledgeRepoEntity, knowledgeBaseEntity);
        if (knowledgeBaseEntity.getExternalId() != null) {
            knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
                .deleteKnowledgeRepo(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId()));
        }
    }

    private void create(String projectId, CreateKnowledgeRepoRequestBody body, String source, String externalId,
        KnowledgeBaseEntity knowledgeBaseEntity, KnowledgeRepoEntity knowledgeRepoEntity) {
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setDisplayName(
                knowledgeRepoEntity.getDisplayName() + "-" + System.currentTimeMillis())
            .setDescription(knowledgeRepoEntity.getDesc())
            .setMetadata(knowledgeRepoEntity.getMetadata())
            .setType(KnowledgeBaseType.INTERNAL)
            .setSource(knowledgeRepoEntity.getSource());
        if (isInternalKnowledgeRepo(KnowledgeBaseType.INTERNAL.toString())) {
            createKnowledgeBaseFromPlatForm(projectId, body, source, knowledgeBaseEntity, knowledgeRepo);
        } else {
            // 引用知识库
            if (StringUtils.isBlank(externalId)) {
                log.error("knowledgeBase id can not be empty");
                throw new AgentBaseException(ErrorCode.EMPTY_PARAM, "knowledge_repo_id");
            }
            setKnowledgeRepoSizeAndFileNums(knowledgeRepo, knowledgeRepoEntity);
            knowledgeRepoMapper.updateByPrimaryKeySelective(knowledgeRepoEntity);
        }
    }

    private void createKnowledgeBaseFromPlatForm(String projectId, CreateKnowledgeRepoRequestBody body, String source,
        KnowledgeBaseEntity knowledgeBaseEntity, KnowledgeRepo knowledgeRepo) {
        // 默认是Exclusive知识库
        String repoType = EXCLUSIVE;
        String tenantType = TenantTypeUtil.getTenantType();
        if (logicKnowledgeRepoEnabled && TENANT_TYPE_2C.equals(tenantType)) {
            repoType = SHARE;
        }
        // 调用知识库平台接口创建知识库
        knowledgeRepo.setEmbeddingModel(getEmbeddingModel(source, body.getEmbeddingModel()))
            .setRerankModel(getReRankModel(source, body.getRerankModel()))
            .setParseConf(Optional.ofNullable(body.getParseConf()).orElse(new ParseConf()))
            .setSplitConf(Optional.ofNullable(body.getSplitConf()).orElse(new SplitConf()))
            .setRagChunkParserConf(Optional.ofNullable(body.getRagChunkParserConf()).orElse(new RagChunkParserConf()))
            .setProjectId(projectId)
            .setRepoType(RepoTypeEnum.fromValue(repoType))
            .setWorkspaceId(knowledgeBaseEntity.getWorkspaceId());
        CreateKnowledgeRepoInfo createKnowledgeRepoInfo = knowledgeRepoContext.getService(source)
            .createKnowledgeRepo(knowledgeRepo);
        knowledgeBaseEntity.setExternalId(createKnowledgeRepoInfo.getKnowledgeBaseId());
        knowledgeBaseEntity.setKnowledgeBaseConnectionId(createKnowledgeRepoInfo.getKnowledgeBaseConnectionId());
        knowledgeBaseEntity.setRepoType(repoType);
        knowledgeBaseMapper.updateKnowledgeBase(projectId, knowledgeBaseEntity);

        // 将连接信息和知识库写入OBS
        writeKbWithConnectionToObs(knowledgeBaseEntity);
    }

    private KnowledgeRepoEntity toKnowledgeRepoEntity(String projectId, CreateKnowledgeRepoRequestBody body) {
        KnowledgeRepoEntity knowledgeRepoEntity = new KnowledgeRepoEntity();
        knowledgeRepoEntity.setKnowledgeRepoId(UUIDGenerator.getUUID());
        knowledgeRepoEntity.setProjectId(projectId);
        knowledgeRepoEntity.setType(KnowledgeBaseType.INTERNAL.toString());
        if (StringUtils.isBlank(body.getIcon())) {
            knowledgeRepoEntity.setIcon(defaultIcon);
        } else {
            IconValidator.validate(body.getIcon(), iconMaxSize, iconType);
            knowledgeRepoEntity.setIcon(body.getIcon());
        }
        knowledgeRepoEntity.setDesc(body.getDescription());
        knowledgeRepoEntity.setDisplayName(body.getDisplayName());
        knowledgeRepoEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());
        knowledgeRepoEntity.setDomainName(RequestContextUtils.getRequestUserDomainName());
        knowledgeRepoEntity.setCreator(RequestContextUtils.getRequestUserName());
        knowledgeRepoEntity.setCreatorId(RequestContextUtils.getRequestUserId());
        knowledgeRepoEntity.setSize(0L);
        knowledgeRepoEntity.setFileNum(0);
        knowledgeRepoEntity.setSource(knowledgeSource);
        knowledgeRepoEntity.setCreatedOn(System.currentTimeMillis() / 1000);
        knowledgeRepoEntity.setUpdatedOn(System.currentTimeMillis() / 1000);
        return knowledgeRepoEntity;
    }

    private KnowledgeBaseEntity toKnowledgeBaseEntity(KnowledgeRepoEntity knowledgeRepoEntity, String workspaceId) {
        return KnowledgeBaseEntity.builder()
            .id(knowledgeRepoEntity.getKnowledgeRepoId())
            .externalId(null)
            .name(knowledgeRepoEntity.getDisplayName())
            .description(knowledgeRepoEntity.getDesc())
            .icon(knowledgeRepoEntity.getIcon())
            .type(KnowledgeBaseType.INTERNAL.getValue())
            .projectId(knowledgeRepoEntity.getProjectId())
            .workspaceId(workspaceId)
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .domainName(RequestContextUtils.getRequestUserDomainName())
            .createdUserId(RequestContextUtils.getRequestUserId())
            .shareScope(ShareScopeEnum.SELF.name())
            .createdUserName(RequestContextUtils.getRequestUserName())
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName())
            .createTime(System.currentTimeMillis())
            .updateTime(System.currentTimeMillis())
            .build();
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "KnowledgeBase",
        description = "删除知识库",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public DeleteOneResponseBody deleteKnowledgeRepo(String projectId, String knowledgeBaseId, String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteKnowledgeBase", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (Objects.isNull(knowledgeBaseEntity)) {
            return null;
        }

        // 自建知识库，需要调用知识库平台接口删除
        if (isInternalKnowledgeRepo(knowledgeBaseEntity.getType())) {
            final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
                projectId);
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setMetadata(knowledgeRepoEntity.getMetadata())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setWorkspaceId(workspaceId);
            knowledgeRepoContext.getService(knowledgeRepoEntity.getSource()).deleteKnowledgeRepo(knowledgeRepo);
            // 删除知识库
            knowledgeRepoMapper.deleteByPrimaryKey(knowledgeBaseId, projectId);
        }

        // 删除知识库
        knowledgeBaseMapper.batchDeleteKnowledgeBase(projectId, Lists.newArrayList(knowledgeBaseId));

        // 删除OBS上的知识库文件
        kbConnectionStorageService.deleteKnowledgeBaseFromObs(knowledgeBaseId);

        // 删除命中测试记录
        knowledgeTestMapper.deleteByRepoId(projectId, knowledgeBaseId);
        // 对于第三方的知识库，如果某个知识源下已经没有知识库了，需要把知识源状态设置为停用
        if (!isInternalKnowledgeRepo(knowledgeBaseEntity.getType())) {
            PageRowBounds pageRowBounds = new PageRowBounds(0, 1);
            List<KnowledgeBaseEntity> knowledgeBaseInConnection = knowledgeBaseMapper.queryKnowledgeBaseList(projectId,
                workspaceId, null, null, null, null, knowledgeBaseEntity.getKnowledgeBaseConnectionId(), null, null,
                null, pageRowBounds);
            if (CollectionUtils.isEmpty(knowledgeBaseInConnection)) {
                knowledgeBaseConnectionMapper.updateKnowledgeBaseConnectionStatus(
                    knowledgeBaseEntity.getKnowledgeBaseConnectionId(), KnowledgeConnectionStatus.CLOSE.toString());
            }
            // 连接信息独立存储，KB删除不影响连接文件
        }
        // 删除obs配置及执行记录
        KnowledgeBaseObsConfigEntity knowledgeBaseObsConfigEntity
            = knowledgeBaseObsConfigMapper.selectByKnowledgeBaseId(knowledgeBaseId);
        if (ObjectUtils.isNotEmpty(knowledgeBaseObsConfigEntity)) {
            knowledgeBaseObsConfigMapper.deleteObsTaskConfig(knowledgeBaseObsConfigEntity.getId());
            knowledgeBaseObsExecuteRecordMapper.deleteExecuteRecordByObsConfigId(knowledgeBaseObsConfigEntity.getId());
        }
        return new DeleteOneResponseBody().setId(knowledgeBaseId);
    }

    @Override
    public CommonDeleteRsp deleteKnowledgeSearchRecord(String projectId, String knowledgeBaseId, String recordId,
        String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteKnowledgeBaseSearchRecord", projectId,
            RequestContextUtils.getRequestUserId());
        int num = knowledgeTestMapper.deleteByPrimaryKey(recordId, knowledgeBaseId, projectId);
        if (num == 0) {
            log.error("knowledgeBase {} can not be empty", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER, recordId);
        }
        return new CommonDeleteRsp().setId(recordId);
    }

    @Override
    public ListExternalKnowledgeBasesResponseBody listExternalKnowledgeBases(String projectId,
        ListExternalKnowledgeBasesQo listExternalKnowledgeBasesQo) {
        ConnectorDefinition definition = getConnectionDefinition(
            listExternalKnowledgeBasesQo.getKnowledgeBaseConnectionId(), listExternalKnowledgeBasesQo.getWorkspaceId());
        PageResult<ExternalKnowledgeBaseInfo> pageResult = knowledgeBaseConnectorContext.listKnowledgeBase(
            listExternalKnowledgeBasesQo.getKnowledgeBaseName(), listExternalKnowledgeBasesQo.getOffset(),
            listExternalKnowledgeBasesQo.getLimit(), definition, RequestContextUtils.getRequestAuthToken());

        ListExternalKnowledgeBasesResponseBody responseBody = new ListExternalKnowledgeBasesResponseBody();
        responseBody.setCount(pageResult.getTotalCount());
        List<ExternalKnowledgeItem> knowledgeItems = pageResult.getItems()
            .stream()
            .map(item -> new ExternalKnowledgeItem().setKnowledgeBaseId(item.getKnowledgeBaseId())
                .setKnowledgeBaseName(item.getKnowledgeBaseName())
                .setDescription(item.getDescription()))
            .toList();
        responseBody.setKnowledgeBaseList(knowledgeItems);
        // 查询下这些第三方知识库是否已经在当前工作空间接入过了
        if (CollectionUtils.isNotEmpty(knowledgeItems)) {
            List<String> externalIds = knowledgeItems.stream().map(ExternalKnowledgeItem::getKnowledgeBaseId).toList();
            List<KnowledgeBaseEntity> knowledgeBaseEntities = knowledgeBaseMapper.batchQueryKnowledgeBases(projectId,
                listExternalKnowledgeBasesQo.getWorkspaceId(), null, externalIds, null);
            Set<String> externalIdsInWorkspace = knowledgeBaseEntities.stream()
                .map(KnowledgeBaseEntity::getExternalId)
                .collect(Collectors.toSet());
            responseBody.getKnowledgeBaseList().forEach(item -> {
                item.setPresent(externalIdsInWorkspace.contains(item.getKnowledgeBaseId()));
            });
        }
        return responseBody;
    }

    @Override
    public KnowledgeSearchRecordRsp listKnowledgeSearchRecords(String projectId, String knowledgeBaseId,
        ListKnowledgeSearchRecordsQo listKnowledgeBaseSearchRecordsQo) {
        PageHelper.offsetPage(listKnowledgeBaseSearchRecordsQo.getOffset(),
            listKnowledgeBaseSearchRecordsQo.getLimit());
        final List<KnowledgeTestEntity> knowledgeTestEntities = knowledgeTestMapper.selectByProjectIdAndRepoId(
            projectId, knowledgeBaseId);
        PageInfo<KnowledgeTestEntity> knowledgeTestEntityPageInfo = new PageInfo<>(knowledgeTestEntities);
        KnowledgeSearchRecordRsp knowledgeSearchRecordRsp = new KnowledgeSearchRecordRsp();
        knowledgeSearchRecordRsp.setCount(knowledgeTestEntityPageInfo.getTotal());
        knowledgeSearchRecordRsp.setKnowledgeSearchRecord(getKnowledgeSearchRecords(knowledgeTestEntities));
        return knowledgeSearchRecordRsp;
    }

    @Override
    public ListKnowledgeTagsResp listKnowledgeRepoTags(String projectId, String knowledgeBaseId,
        ListKnowledgeRepoTagsQo listKnowledgeBaseTagsQo) {

        // CUSTOM暂不支持查询标签列表
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            return new ListKnowledgeTagsResp().setCount(0).setTagList(Collections.emptyList());
        }

        // 非CUSTOM知识库，会在数据库中有记录
        KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (knowledgeBase == null) {
            log.error("knowledgeBase {} can not be empty", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, knowledgeBaseId);
        }
        // 对于默认的知识库，调用内部知识库查询
        if (KnowledgeBaseType.fromValue(knowledgeBase.getType()) == KnowledgeBaseType.INTERNAL) {
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId());
            final KnowledgeRepoEntity knowledgeRepoEntity = checkKnowledgeRepoExist(knowledgeBaseId);
            knowledgeRepo.setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()));
            knowledgeRepo.setMetadata(knowledgeRepoEntity.getMetadata());

            int limit = listKnowledgeBaseTagsQo.getLimit();
            int offset = listKnowledgeBaseTagsQo.getOffset();
            return knowledgeRepoContext.getService(knowledgeSource)
                .listKnowledgeRepoTags(knowledgeRepo, offset / limit + 1, limit);
        } else {
            // 对于外部的知识库，从第三方的知识源中查询标签
            ConnectorDefinition connectorDefinition = getConnectionDefinition(
                knowledgeBase.getKnowledgeBaseConnectionId(), null);
            List<KnowledgeBaseTagInfo> allTags = knowledgeBaseConnectorContext.listKnowledgeBaseTags(
                knowledgeBase.getExternalId(), connectorDefinition);
            ListKnowledgeTagsResp resp = new ListKnowledgeTagsResp();
            resp.setCount(allTags.size());
            List<KnowledgeBaseTagInfo> result = AgentBaseListUtil.slice(allTags, listKnowledgeBaseTagsQo.getOffset(),
                listKnowledgeBaseTagsQo.getLimit());
            List<KnowledgeTagInfo> list = result.stream()
                .map(item -> new KnowledgeTagInfo().setId(item.getId()).setName(item.getName()))
                .toList();
            resp.setTagList(list);
            return resp;
        }
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "KnowledgeBase",
        description = "创建知识库标签",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public CreateKnowledgeRepoTagsRsp createKnowledgeRepoTags(String projectId, String workspaceId,
        String knowledgeBaseId, CreateKnowledgeRepoTagsReq body) {
        // CUSTOM暂不支持标签创建
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            log.warn("do not support createKnowledgeBaseTags yet");
            throw new AgentBaseException("do not support createKnowledgeBaseTags yet");
        }

        // 非CUSTOM知识库，会在数据库中有记录
        KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (knowledgeBase == null) {
            log.error("knowledgeBase {} can not be empty", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }
        if (KnowledgeBaseType.fromValue(knowledgeBase.getType()) == KnowledgeBaseType.INTERNAL) {
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId());
            final KnowledgeRepoEntity knowledgeRepoEntity = checkKnowledgeRepoExist(knowledgeBaseId);
            knowledgeRepo.setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()));
            knowledgeRepo.setMetadata(knowledgeRepoEntity.getMetadata());
            return knowledgeRepoContext.getService(knowledgeSource).createKnowledgeRepoTags(knowledgeRepo, body);
        } else {
            log.warn("External knowledgebase do not support createKnowledgeBaseTags yet");
            throw new AgentBaseException("External knowledgebase do not support createKnowledgeBaseTags yet");
        }
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "KnowledgeBase",
        description = "删除知识库标签",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public DeleteKnowledgeRepoTagsRsp deleteKnowledgeRepoTags(String projectId, String workspaceId,
        String knowledgeBaseId, String tagId, DeleteKnowledgeRepoTagsReq body) {
        // CUSTOM暂不支持标签创建
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            log.warn("do not support deleteKnowledgeBaseTags yet");
            throw new AgentBaseException("do not support deleteKnowledgeBaseTags yet");
        }

        // 非CUSTOM知识库，会在数据库中有记录
        KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (knowledgeBase == null) {
            log.error("knowledgeBase {} can not be empty", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }
        if (KnowledgeBaseType.fromValue(knowledgeBase.getType()) == KnowledgeBaseType.INTERNAL) {
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId());
            final KnowledgeRepoEntity knowledgeRepoEntity = checkKnowledgeRepoExist(knowledgeBaseId);
            knowledgeRepo.setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()));
            knowledgeRepo.setMetadata(knowledgeRepoEntity.getMetadata());
            return knowledgeRepoContext.getService(knowledgeSource).deleteKnowledgeRepoTags(knowledgeRepo, tagId, body);
        } else {
            log.warn("External knowledgebase do not support deleteKnowledgeBaseTags yet");
            throw new AgentBaseException("External knowledgebase do not support deleteKnowledgeBaseTags yet");
        }
    }

    @Override
    public ListKnowledgeModelsResponseBody listKnowledgeModels(String projectId, ListKnowledgeModelsQo listModelsQo) {
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
        if (NO_CONNECTOR.equals(connectionId)) {
            return new ListKnowledgeModelsResponseBody().setTotal(0).setModels(Collections.emptyList());
        }
        KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseMapper.selectById(projectId, listModelsQo.getRepoId());
        List<ModelInfo> modelInfos = knowledgeRepoContext.getService(knowledgeSource)
            .listModels(ModelSearchCriteria.builder()
                .modelName(listModelsQo.getModelName())
                .modelType(listModelsQo.getModelType())
                .repoId(Optional.ofNullable(knowledgeBaseEntity).map(KnowledgeBaseEntity::getExternalId).orElse(null))
                .modelStatus(NORMAL_MODEL_STATUS)
                .pageNum(listModelsQo.getOffset() / listModelsQo.getLimit() + 1)
                .pageSize(listModelsQo.getLimit())
                .build(), connectionId);
        return new ListKnowledgeModelsResponseBody().setTotal(modelInfos.size()).setModels(modelInfos);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBase",
        description = "修改知识库可见性",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public UpdateKnowledgeVisibilityResponse modifyKnowledgeBaseVisibility(String projectId, String knowledgeBaseId,
        String workspaceId, PermissionsRequestBody body) {
        final KnowledgeBaseEntity knowledgeBase = checkKnowledgeBaseExist(knowledgeBaseId);
        if (KnowledgeRepoStatus.CLOSE.equals(KnowledgeRepoStatus.fromValue(knowledgeBase.getStatus()))) {
            log.error("Knowledge_base {} is close, can not update", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_CLOSED_OPERATION_FORBIDDEN);
        }
        changeKnowledgeBaseShareScope(knowledgeBase, body);
        PermissionsRequestBody.ShareScopeEnum shareScope = body.getShareScope();
        KnowledgeBaseEntity knowledgeBaseEntity = new KnowledgeBaseEntity();
        knowledgeBaseEntity.setId(knowledgeBaseId);
        knowledgeBaseEntity.setProjectId(projectId);
        knowledgeBaseEntity.setShareScope(shareScope.name());
        knowledgeBaseMapper.updateKnowledgeBase(projectId, knowledgeBaseEntity);
        return new UpdateKnowledgeVisibilityResponse().setId(knowledgeBaseId);
    }

    private void changeKnowledgeBaseShareScope(KnowledgeBaseEntity knowledgeBase, PermissionsRequestBody body) {
        long now = System.currentTimeMillis();
        String requestUserId = RequestContextUtils.getRequestUserId();
        String requestUserName = RequestContextUtils.getRequestUserName();
        if (body.getShareScope() == null) {
            return;
        }
        switch (body.getShareScope()) {
            case PARTIAL -> {
                List<String> targetWorkspaces = body.getAuthWorkspaceIdList();
                if (CollectionUtils.isEmpty(targetWorkspaces)) {
                    knowledgeShareScopeMapper.deleteKnowledgeBase(knowledgeBase.getProjectId(), knowledgeBase.getId());
                    return;
                }
                // 查询现有共享空间
                Set<String> existing = knowledgeShareScopeMapper.findByKnowledgeBaseId(knowledgeBase.getId())
                    .stream()
                    .map(KnowledgeShareScopeEntity::getWorkspaceId)
                    .collect(Collectors.toSet());
                // 新增：未存在的空间
                List<KnowledgeShareScopeEntity> inserts = targetWorkspaces.stream()
                    .filter(w -> !existing.contains(w))
                    .map(w -> KnowledgeShareScopeEntity.builder()
                        .id(UUIDGenerator.getUUID())
                        .knowledgeBaseId(knowledgeBase.getId())
                        .createdUserId(requestUserId)
                        .createdUserName(requestUserName)
                        .createTime(now)
                        .projectId(knowledgeBase.getProjectId())
                        .workspaceId(w)
                        .build())
                    .collect(Collectors.toList());
                if (!inserts.isEmpty()) {
                    knowledgeShareScopeMapper.batchInsert(inserts);
                }
                // 删除：不再需要的共享
                List<String> deletes = existing.stream()
                    .filter(w -> !targetWorkspaces.contains(w))
                    .collect(Collectors.toList());
                if (!deletes.isEmpty()) {
                    knowledgeShareScopeMapper.deleteByWorkspaceIdsAndKnowledgeBaseId(knowledgeBase.getProjectId(),
                        knowledgeBase.getId(), deletes);
                }
            }
            case SELF, GLOBAL ->
                knowledgeShareScopeMapper.deleteKnowledgeBase(knowledgeBase.getProjectId(), knowledgeBase.getId());
        }
    }

    @Override
    public ShowKnowledgeRepoResponseBody showKnowledgeRepo(String projectId, String knowledgeBaseId,
        String workspaceId) {
        final KnowledgeBaseEntity knowledgeBase = checkKnowledgeBaseExist(knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, workspaceId, knowledgeBase);
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
            projectId);
        final KnowledgeRepo knowledgeRepo = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .retrieveKnowledgeRepo(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata())
                .setWorkspaceId(workspaceId));
        final ShowKnowledgeRepoResponseBody showKnowledgeRepoResponseBody = new ShowKnowledgeRepoResponseBody();
        BeanUtils.copyProperties(knowledgeRepo, showKnowledgeRepoResponseBody);
        showKnowledgeRepoResponseBody.setRepoType(RepoTypeEnum.fromValue(knowledgeBase.getRepoType()) == null
            ? RepoTypeEnum.EXCLUSIVE.getValue()
            : RepoTypeEnum.fromValue(knowledgeBase.getRepoType()).getValue());
        showKnowledgeRepoResponseBody.setKnowledgeRepoId(knowledgeBaseId);
        showKnowledgeRepoResponseBody.setProjectId(projectId);
        showKnowledgeRepoResponseBody.setDisplayName(knowledgeRepoEntity.getDisplayName());
        showKnowledgeRepoResponseBody.setDescription(knowledgeRepoEntity.getDesc());
        showKnowledgeRepoResponseBody.setIcon(knowledgeRepoEntity.getIcon());
        showKnowledgeRepoResponseBody.setCreator(knowledgeRepoEntity.getCreator());
        showKnowledgeRepoResponseBody.setSize(knowledgeRepoEntity.getSize());
        showKnowledgeRepoResponseBody.setIconName(knowledgeRepoEntity.getIconName());
        showKnowledgeRepoResponseBody.setType(
            ShowKnowledgeRepoResponseBody.TypeEnum.fromValue(knowledgeBase.getType()));
        if (StringUtils.isNotEmpty(knowledgeRepo.getMetadata())) {
            showKnowledgeRepoResponseBody.setMetadata(displayMetadata(knowledgeRepoEntity.getMetadata()));
        }
        showKnowledgeRepoResponseBody.setCreateTime(knowledgeRepoEntity.getCreatedOn());
        showKnowledgeRepoResponseBody.setUpdateTime(knowledgeRepoEntity.getUpdatedOn());
        showKnowledgeRepoResponseBody.setWorkspaceId(knowledgeBase.getWorkspaceId());
        showKnowledgeRepoResponseBody.setShareScope(ShowKnowledgeRepoResponseBody.ShareScopeEnum.fromValue(knowledgeBase.getShareScope()));
        showKnowledgeRepoResponseBody.setUpdateUserName(knowledgeBase.getLastUpdateUserName());
        showKnowledgeRepoResponseBody.setStatus(
            Optional.ofNullable(knowledgeRepo.getStatus()).orElse(knowledgeRepoEntity.getStatus()));
        Long maxSize = resourceValidateService.queryQuotaLimit(ResourceType.KNOWLEDGE_BASE_DATESET_STORAGE);
        Long usedSize = resourceUsageFactory.chooseResourceUsageQueryServiceMap(
                ResourceType.KNOWLEDGE_BASE_DATESET_STORAGE)
            .queryResourceUsageCount(RequestContextUtils.getRequestUserDomainId());
        showKnowledgeRepoResponseBody.setMaxSize(maxSize);
        showKnowledgeRepoResponseBody.setRemainSize(Math.max(maxSize - usedSize, 0));
        return showKnowledgeRepoResponseBody;
    }

    /**
     * 命中测试，只用来测试某个知识库中的检索结果，不提供给其他模块使用，需要记录命中测试历史
     *
     * @param projectId projectId
     * @param offset offset
     * @param limit limit
     * @param body body
     * @return
     */
    @Override
    public SearchKnowledgeRepoResponseBody searchKnowledgeRepo(String projectId, String workspaceId, Integer offset,
        Integer limit, SearchKnowledgeRepoRequestBody body) {
        log.info("knowledgeBase body is {}", JacksonUtils.toJson(body));
        final KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectById(projectId, body.getKnowledgeRepoId());
        if (Objects.isNull(knowledgeBase)) {
            log.error("knowledgeBase {} can not be empty", body.getKnowledgeRepoId());
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, body.getKnowledgeRepoId());
        }
        ShareScopeValidUtil.checkKnowledgeScope(body.getKnowledgeRepoId(), workspaceId, knowledgeBase);
        SearchTextResp searchTextResp = null;
        SearchKnowledgeRepoResponseBody knowledgeSearchRsp = new SearchKnowledgeRepoResponseBody();
        if (isInternalKnowledgeRepo(knowledgeBase.getType())) {
            final KnowledgeRepoEntity knowledgeRepoEntity = checkKnowledgeRepoExist(body.getKnowledgeRepoId());
            int pageNum = offset / limit + 1;
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata());
            searchTextResp = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
                .searchText(Lists.newArrayList(knowledgeRepo), body.getQuery(), body.getSearchMode().toString(), null,
                    pageNum, limit);
            knowledgeSearchRsp.setTotal(searchTextResp.getTotal());
            knowledgeSearchRsp.setSearchResultList(
                Optional.of(searchTextResp).map(SearchTextResp::getDocList).orElse(Collections.emptyList()));
            // 处理切片中的图片信息
            knowledgeSearchRsp.getSearchResultList().forEach(item -> {
                List<String> imageIds = ChunkUtils.extractImageId(item.getContent());
                if (CollectionUtils.isNotEmpty(imageIds)) {
                    item.setContent(ChunkUtils.removeImageId(item.getContent()));
                    item.setImageIds(imageIds);
                    List<String> imagePaths = new ArrayList<>();
                    imageIds.forEach(imageId -> {
                        imagePaths.add(
                            ChunkUtils.generateChunkImageUriPath(projectId, body.getKnowledgeRepoId(), imageId));
                    });
                    item.setImagePaths(imagePaths);
                }
            });
        } else {
            ConnectorDefinition connectorDefinition = getConnectionDefinition(
                knowledgeBase.getKnowledgeBaseConnectionId(), null);
            RetrieveKnowledgeBaseReq retrieveKnowledge = new RetrieveKnowledgeBaseReq();
            KnowledgeBaseRetrieval knowledgeBaseRetrieval = new KnowledgeBaseRetrieval();
            knowledgeBaseRetrieval.setKnowledgeBaseId(knowledgeBase.getExternalId());
            retrieveKnowledge.setKnowledgeBaseRetrievals(Lists.newArrayList(knowledgeBaseRetrieval));
            retrieveKnowledge.setQuery(body.getQuery());
            retrieveKnowledge.setQueryMode(QueryModeEnum.valueOf(body.getSearchMode().name()));
            PageResult<ExternalRetrieveResultInfo> retrieveResult = knowledgeBaseConnectorContext.retrieveKnowledgeBase(
                retrieveKnowledge, offset, limit, connectorDefinition, RequestContextUtils.getRequestAuthToken());

            knowledgeSearchRsp.setTotal(retrieveResult.getTotalCount().intValue());
            List<ChatReferenceInfo> list = retrieveResult.getItems()
                .stream()
                .map(item -> new ChatReferenceInfo().setRepoId(item.getKnowledgeBaseId())
                    .setFileId(item.getFileId())
                    .setChunkId(item.getChunkId())
                    .setTitle(item.getTitle())
                    .setSubtitle(item.getTitle())
                    .setContent(item.getContent())
                    .setScore(item.getScore())
                    .setImageIds(item.getImageIds())
                    .setImagePaths(item.getImagePaths()))
                .toList();
            knowledgeSearchRsp.setSearchResultList(list);
        }
        // 测试命中记录入库
        recordSearchKnowledgeRepo(projectId, body);
        return knowledgeSearchRsp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBase",
        description = "启用知识库",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public StartKnowledgeRepoResponseBody startKnowledgeRepo(String projectId, String knowledgeBaseId,
        String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, startKnowledgeBase", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBase = checkKnowledgeBaseExist(knowledgeBaseId);

        if (isInternalKnowledgeRepo(knowledgeBase.getType())) {
            // 调用知识库接口启用知识库
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeBase.getType()));
            knowledgeRepoContext.getService(knowledgeSource).startKnowledgeRepo(knowledgeRepo);

            // 更新数据库
            KnowledgeRepoEntity newKnowledgeRepo = new KnowledgeRepoEntity();
            newKnowledgeRepo.setKnowledgeRepoId(knowledgeBaseId);
            newKnowledgeRepo.setDomainId(RequestContextUtils.getRequestUserDomainId());
            newKnowledgeRepo.setStatus(KnowledgeRepoStatus.OPEN.toString());
            newKnowledgeRepo.setProjectId(projectId);
            newKnowledgeRepo.setUpdatedOn(System.currentTimeMillis() / 1000);
            knowledgeRepoMapper.updateByPrimaryKeySelective(newKnowledgeRepo);
        }

        KnowledgeBaseEntity knowledgeBaseEntity = new KnowledgeBaseEntity();
        knowledgeBaseEntity.setId(knowledgeBaseId);
        knowledgeBaseEntity.setStatus(KnowledgeRepoStatus.OPEN.toString());
        knowledgeBaseEntity.setUpdateTime(System.currentTimeMillis());
        knowledgeBaseMapper.updateKnowledgeBase(projectId, knowledgeBaseEntity);
        return new StartKnowledgeRepoResponseBody().setId(knowledgeBaseId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBase",
        description = "停用知识库",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public StopKnowledgeRepoResponseBody stopKnowledgeRepo(String projectId, String knowledgeBaseId,
        String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, stopKnowledgeRepo", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBase = checkKnowledgeBaseExist(knowledgeBaseId);

        String scopeEnum = knowledgeBase.getShareScope();
        if (ShareScopeEnum.GLOBAL.equals(ShareScopeEnum.fromValue(scopeEnum))) {
            log.error("knowledge base {} is global, can not stop it.", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_CAN_NOT_CLOSE_FOR_PUBLISH);
        }

        if (isInternalKnowledgeRepo(knowledgeBase.getType())) {
            // 调用知识库接口停用知识库
            KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeBase.getType()));
            knowledgeRepoContext.getService(knowledgeSource).stopKnowledgeRepo(knowledgeRepo);

            // 更新数据库
            KnowledgeRepoEntity newKnowledgeRepo = new KnowledgeRepoEntity();
            newKnowledgeRepo.setKnowledgeRepoId(knowledgeBaseId);
            newKnowledgeRepo.setDomainId(RequestContextUtils.getRequestUserDomainId());
            newKnowledgeRepo.setStatus(KnowledgeRepoStatus.CLOSE.toString());
            newKnowledgeRepo.setProjectId(projectId);
            newKnowledgeRepo.setUpdatedOn(System.currentTimeMillis() / 1000);
            knowledgeRepoMapper.updateByPrimaryKeySelective(newKnowledgeRepo);
        }

        KnowledgeBaseEntity knowledgeBaseEntity = new KnowledgeBaseEntity();
        knowledgeBaseEntity.setId(knowledgeBaseId);
        knowledgeBaseEntity.setStatus(KnowledgeRepoStatus.CLOSE.toString());
        knowledgeBaseEntity.setUpdateTime(System.currentTimeMillis());
        knowledgeBaseMapper.updateKnowledgeBase(projectId, knowledgeBaseEntity);
        return new StopKnowledgeRepoResponseBody().setId(knowledgeBaseId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBase",
        description = "修改知识库",
        resourceId = "knowledgeBaseId",
        resourceName = "body.displayName"
    )
    public ModifyKnowledgeRepoResponseBody modifyKnowledgeRepo(String projectId, String knowledgeBaseId,
        String workspaceId, ModifyKnowledgeRepoRequestBody body) {
        final KnowledgeBaseEntity knowledgeBase = checkKnowledgeBaseExist(knowledgeBaseId);

        if (KnowledgeRepoStatus.OPEN.toString().equals(knowledgeBase.getStatus())) {
            log.warn("Knowledge base {} is open, can not update.", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_CAN_NOT_UPDATE_FOR_OPEN,
                String.join(",", knowledgeBaseId));
        }

        String newEncryptMetadata = encryptMetadata(body.getMetadata());
        // 自建知识库，需要调用知识库平台接口更新
        if (isInternalKnowledgeRepo(knowledgeBase.getType())) {
            final KnowledgeRepoEntity oldKnowledgeRepo = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
                projectId);
            // 如果更新模型不为空，则要判断注册模型
            String source = oldKnowledgeRepo.getSource();
            if (!Objects.equals(body.getDisplayName(), oldKnowledgeRepo.getDisplayName()) || !Objects.isNull(
                body.getRerankModel()) || !Objects.isNull(body.getParseConf()) || !Objects.isNull(body.getSplitConf())
                || !Objects.isNull(body.getRagChunkParserConf())) {
                // 更新知识库设置
                String realName = body.getDisplayName() + "-" + System.currentTimeMillis();
                KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBase.getExternalId())
                    .setDisplayName(realName)
                    .setWorkspaceId(workspaceId)
                    .setMetadata(
                        StringUtils.isBlank(body.getMetadata()) ? oldKnowledgeRepo.getMetadata() : newEncryptMetadata);

                if (!Objects.isNull(body.getRerankModel())) {
                    knowledgeRepo.setRerankModel(body.getRerankModel().getName());

                }
                Optional.ofNullable(body.getDescription()).ifPresent(knowledgeRepo::setDescription);
                Optional.ofNullable(body.getParseConf()).ifPresent(knowledgeRepo::setParseConf);
                Optional.ofNullable(body.getSplitConf()).ifPresent(knowledgeRepo::setSplitConf);
                Optional.ofNullable(body.getRagChunkParserConf()).ifPresent(knowledgeRepo::setRagChunkParserConf);
                knowledgeRepoContext.getService(source).modifyKnowledgeRepo(knowledgeRepo);
            }
        }

        // 更新数据库
        KnowledgeRepoEntity knowledgeRepo = new KnowledgeRepoEntity();
        knowledgeRepo.setKnowledgeRepoId(knowledgeBaseId);
        knowledgeRepo.setProjectId(projectId);
        knowledgeRepo.setDisplayName(body.getDisplayName());
        knowledgeRepo.setDesc(body.getDescription());
        knowledgeRepo.setMetadata(newEncryptMetadata);
        knowledgeRepo.setDomainId(RequestContextUtils.getRequestUserDomainId());
        knowledgeRepo.setDomainName(RequestContextUtils.getRequestUserDomainName());
        knowledgeRepo.setUpdatedOn(System.currentTimeMillis() / 1000);
        if (StringUtils.isBlank(body.getIcon())) {
            knowledgeRepo.setIcon(knowledgeBase.getIcon());
        } else {
            IconValidator.validate(body.getIcon(), iconMaxSize, iconType);
            knowledgeRepo.setIcon(body.getIcon());
        }
        knowledgeRepoMapper.updateByPrimaryKeySelective(knowledgeRepo);
        KnowledgeBaseEntity knowledgeBaseEntity = KnowledgeBaseEntity.builder()
            .id(knowledgeBaseId)
            .name(body.getDisplayName())
            .icon(knowledgeRepo.getIcon())
            .description(body.getDescription())
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName())
            .updateTime(System.currentTimeMillis())
            .build();
        knowledgeBaseMapper.updateKnowledgeBase(projectId, knowledgeBaseEntity);
        return new ModifyKnowledgeRepoResponseBody().setKnowledgeRepoId(knowledgeBaseId);
    }

    private List<KnowledgeSearchRecord> getKnowledgeSearchRecords(List<KnowledgeTestEntity> knowledgeTestEntities) {
        List<KnowledgeSearchRecord> searchRecords = new ArrayList<>();
        for (KnowledgeTestEntity knowledgeTest : knowledgeTestEntities) {
            KnowledgeSearchRecord searchRecord = new KnowledgeSearchRecord();
            searchRecord.setId(knowledgeTest.getRecordId());
            searchRecord.setQuery(knowledgeTest.getQuery());
            searchRecord.setCreateTime(knowledgeTest.getCreatedOn());
            searchRecords.add(searchRecord);
        }
        return searchRecords;
    }

    private KnowledgeRepoEntity checkKnowledgeRepoExist(String knowledgeRepoId) {
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeRepoId,
            RequestContextUtils.getRequestProjectId());
        if (Objects.isNull(knowledgeRepoEntity)) {
            log.error("knowledgeBase {} can not be empty", knowledgeRepoId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, knowledgeRepoId);
        }
        return knowledgeRepoEntity;
    }

    private KnowledgeBaseEntity checkKnowledgeBaseExist(String knowledgeBaseId) {
        final KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectById(
            RequestContextUtils.getRequestProjectId(), knowledgeBaseId);
        if (Objects.isNull(knowledgeBase)) {
            log.error("knowledgeBase {} can not be empty", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, knowledgeBaseId);
        }
        return knowledgeBase;
    }

    private void recordSearchKnowledgeRepo(String projectId, SearchKnowledgeRepoRequestBody body) {
        KnowledgeTestEntity knowledgeTest = new KnowledgeTestEntity();
        knowledgeTest.setRecordId(UUID.randomUUID().toString());
        knowledgeTest.setKnowledgeRepoId(body.getKnowledgeRepoId());
        knowledgeTest.setQuery(body.getQuery());
        knowledgeTest.setProjectId(projectId);
        knowledgeTest.setDomainId(RequestContextUtils.getRequestUserDomainId());
        knowledgeTest.setDomainName(RequestContextUtils.getRequestUserDomainName());
        knowledgeTest.setCreatedOn(System.currentTimeMillis() / 1000);
        knowledgeTestMapper.insert(knowledgeTest);
    }

    private boolean isInternalKnowledgeRepo(String type) {
        return KnowledgeBaseType.INTERNAL.toString().equalsIgnoreCase(type);
    }

    /**
     * 将知识库信息和连接信息分别写入OBS
     * <p>
     * 在知识库创建成功并关联到connection后调用此方法。
     * 知识库文件和连接文件独立存储，修改连接时只需更新连接文件。
     * 对于默认 LakeSearch 连接，需要注入 YAML 配置中的 project_id 和 application_id。
     * </p>
     *
     * @param knowledgeBaseEntity 知识库实体（必须已设置knowledgeBaseConnectionId）
     */
    private void writeKbWithConnectionToObs(KnowledgeBaseEntity knowledgeBaseEntity) {
        try {
            // 写入知识库文件（仅含知识库自身信息 + connectionId 引用）
            kbConnectionStorageService.writeKnowledgeBaseToObs(knowledgeBaseEntity);

            // 写入连接文件（独立存储，同一连接的所有知识库共享）
            String connectionId = knowledgeBaseEntity.getKnowledgeBaseConnectionId();
            if (StringUtils.isNotEmpty(connectionId)) {
                KnowledgeBaseConnectionEntity connectionEntity = knowledgeBaseConnectionMapper.findById(connectionId);
                if (connectionEntity != null) {
                    String connectorType = connectionEntity.getConnectorType();
                    String connectorName = connectionEntity.getConnectorName();

                    // 判断是否为默认 LakeSearch 内部连接，需要注入 YAML 配置项
                    boolean isLakeSearchInside = "inside".equals(connectorType)
                        && "LakeSearchInside".equals(connectionEntity.getConnectorId());
                    if (isLakeSearchInside) {
                        kbConnectionStorageService.syncDefaultConnectionToObs(
                            connectionEntity, connectorType, connectorName,
                            lakeSearchProjectId, lakeSearchApplicationId);
                    } else {
                        kbConnectionStorageService.writeConnectionToObs(
                            connectionEntity, connectorType, connectorName);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Write knowledge base with connection to OBS failed. knowledgeBaseId: {}",
                knowledgeBaseEntity.getId(), e);
            // OBS写入失败不影响主流程，仅记录日志
        }
    }

    private void setKnowledgeRepoSizeAndFileNums(KnowledgeRepo knowledgeRepo, KnowledgeRepoEntity knowledgeRepoEntity) {
        long size = 0L;
        List<FileInfo> files = getAllFiles(knowledgeRepo);
        for (FileInfo fileInfo : files) {
            size += fileInfo.getFileSize();
        }
        knowledgeRepoEntity.setSize(size);
        knowledgeRepoEntity.setFileNum(files.size());
    }

    private List<FileInfo> getAllFiles(KnowledgeRepo knowledgeRepo) {
        int pageNum = 1;
        ListKnowledgeFilesResponseBody fileInfoListRsp = knowledgeRepoContext.getService(knowledgeRepo.getSource())
            .listFiles(knowledgeRepo,
                new ListFileReq().setFileName(null).setPageNum(pageNum).setPageSize(CommonConstant.MAX_PAGE_SIZE));
        int total = fileInfoListRsp.getCount();
        if (total == 0) {
            return new ArrayList<>();
        }
        List<FileInfo> allFiles = new ArrayList<>(fileInfoListRsp.getFileInfoList());

        // 知识库文件总数量大于单次查询的上限，分多次循环查询
        if (total > CommonConstant.MAX_PAGE_SIZE) {
            for (int i = 0; i < total / CommonConstant.MAX_PAGE_SIZE; i++) {
                pageNum++;
                List<FileInfo> tempFileInfos = knowledgeRepoContext.getService(knowledgeRepo.getSource())
                    .listFiles(knowledgeRepo, new ListFileReq().setFileName(null)
                        .setPageNum(pageNum)
                        .setPageSize(CommonConstant.MAX_PAGE_SIZE))
                    .getFileInfoList();
                if (CollectionUtils.isEmpty(tempFileInfos)) {
                    break;
                }
                allFiles.addAll(tempFileInfos);
            }
        }
        // 根据文件id进行去重
        return allFiles.stream()
            .collect(
                collectingAndThen(toCollection(() -> new TreeSet<>(comparing(FileInfo::getFileId))), ArrayList::new));
    }

    // 对metadata中的秘钥信息进行加密
    private String encryptMetadata(String metadata) {
        if (StringUtils.isNotEmpty(metadata)) {
            KnowledgeRepoMetadata knowledgeRepoMetadata = JacksonUtils.readValue(metadata, KnowledgeRepoMetadata.class);
            if (Objects.isNull(knowledgeRepoMetadata)) {
                return metadata;
            }
            knowledgeRepoMetadata.setAuthorization(CryptoUtils.encrypt(knowledgeRepoMetadata.getAuthorization()));
            return JacksonUtils.toJson(knowledgeRepoMetadata);
        }
        return null;
    }

    // 展示metadata，需要将其中的秘钥信息置空
    private String displayMetadata(String metadata) {
        KnowledgeRepoMetadata knowledgeRepoMetadata = JacksonUtils.readValue(metadata, KnowledgeRepoMetadata.class);
        if (Objects.isNull(knowledgeRepoMetadata)) {
            return metadata;
        }
        knowledgeRepoMetadata.setAuthorization(null);
        return JacksonUtils.toJson(knowledgeRepoMetadata);
    }

    private String getEmbeddingModel(String source, ModelConf modelConf) {
        if (!Objects.isNull(modelConf)) {
            return modelConf.getName();
        }
        log.info("Get embedding model name from env when create knowledge repo.");
        return KnowledgeSourceEnum.KOOSEARCH.toString().equalsIgnoreCase(source)
            ? kosEmbeddingModel
            : mrsEmbeddingModel;
    }

    private String getReRankModel(String source, ModelConf modelConf) {
        if (!Objects.isNull(modelConf)) {
            return modelConf.getName();
        }
        log.info("Get reRank model name from env when create knowledge repo.");
        return KnowledgeSourceEnum.KOOSEARCH.toString().equalsIgnoreCase(source) ? kosReRankModel : mrsReRankModel;
    }


    public ListKnowledgeBasesResponseBody listKnowledgeBaseByShareScope(String projectId,
        ListKnowledgeBasesQo listKnowledgeBaseQo) {
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            ListKnowledgeBaseParamsForCustom paramsForCustom = ListKnowledgeBaseParamsForCustom.builder()
                .knowledgeBaseIds(listKnowledgeBaseQo.getKnowledgeBaseIds())
                .name(listKnowledgeBaseQo.getName())
                .offset(listKnowledgeBaseQo.getOffset())
                .limit(listKnowledgeBaseQo.getLimit())
                .knowledgeBaseType(listKnowledgeBaseQo.getKnowledgeBaseType())
                .build();
            return listKnowledgeBaseForCustom(paramsForCustom);
        }

        PageRowBounds pageRowBounds = new PageRowBounds(listKnowledgeBaseQo.getOffset(),
            listKnowledgeBaseQo.getLimit());
        String realQueryName = SqlLikeEscapeHelper.escapeLikeCharacters(listKnowledgeBaseQo.getName());
        List<KnowledgeBaseEntity> items = knowledgeBaseMapper.queryKnowledgeBaseList(projectId, null, null,
            realQueryName, null, listKnowledgeBaseQo.getType(), listKnowledgeBaseQo.getStatus(),
            listKnowledgeBaseQo.getKnowledgeBaseConnectionId(), null, listKnowledgeBaseQo.getKnowledgeBaseIds(),
            pageRowBounds);
        List<String> connectionIds = items.stream()
            .map(KnowledgeBaseEntity::getKnowledgeBaseConnectionId)
            .filter(StringUtils::isNotEmpty)
            .toList();
        final Map<String, KnowledgeBaseConnection> connectionMap = Maps.newHashMap();
        if (CollectionUtils.isNotEmpty(connectionIds)) {
            List<KnowledgeBaseConnection> connections
                = knowledgeBaseConnectionMapper.batchQueryKnowledgeBaseConnections(connectionIds, null);
            connectionMap.putAll(
                connections.stream().collect(Collectors.toMap(KnowledgeBaseConnection::getId, item -> item)));
        }
        List<KnowledgeBaseListItem> resultList = ObjectUtils.firstNonNull(items,
                Collections.<KnowledgeBaseEntity>emptyList())
            .stream()
            .map(item -> new KnowledgeBaseListItem().setKnowledgeBaseId(item.getId())
                .setType(KnowledgeBaseListItem.TypeEnum.fromValue(item.getType()))
                .setName(item.getName())
                .setIcon(item.getIcon())
                .setDescription(item.getDescription())
                .setStatus(KnowledgeBaseListItem.StatusEnum.fromValue(item.getStatus()))
                // 对于第三方知识库，需要额外补充知识源和前台页面跳转地址
                .setSource(convertConnectionToSource(item, connectionMap.get(item.getKnowledgeBaseConnectionId())))
                .setWorkspaceId(item.getWorkspaceId())
                .setRepoType(KnowledgeBaseListItem.RepoTypeEnum.fromValue(item.getRepoType()) == null
                    ? KnowledgeBaseListItem.RepoTypeEnum.EXCLUSIVE
                    : KnowledgeBaseListItem.RepoTypeEnum.fromValue(item.getRepoType()))
                .setKnowledgeBaseConnectionId(item.getKnowledgeBaseConnectionId())
                .setCreatedUserId(item.getCreatedUserId())
                .setCreatedUserName(item.getCreatedUserName())
                .setCreateTime(item.getCreateTime())
                .setLastUpdateUserId(item.getLastUpdateUserId())
                .setLastUpdateUserName(item.getLastUpdateUserName())
                .setUpdateTime(item.getUpdateTime())
                .setShareScope(KnowledgeBaseListItem.ShareScopeEnum.fromValue(item.getShareScope())))
            .toList();
        ListKnowledgeBasesResponseBody response = new ListKnowledgeBasesResponseBody();
        response.setTotal(pageRowBounds.getTotal());
        response.setItems(resultList);
        return response;
    }


    /**
     * 查询知识库列表（V2接口）
     *
     * @param projectId projectId
     * @param listKnowledgeBaseQo listKnowledgeBaseQo
     * @return
     */
    @Override
    public ListKnowledgeBasesResponseBody listKnowledgeBases(String projectId,
        ListKnowledgeBasesQo listKnowledgeBaseQo) {

        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            ListKnowledgeBaseParamsForCustom paramsForCustom = ListKnowledgeBaseParamsForCustom.builder()
                .knowledgeBaseIds(listKnowledgeBaseQo.getKnowledgeBaseIds())
                .name(listKnowledgeBaseQo.getName())
                .offset(listKnowledgeBaseQo.getOffset())
                .limit(listKnowledgeBaseQo.getLimit())
                .knowledgeBaseType(listKnowledgeBaseQo.getKnowledgeBaseType())
                .build();
            return listKnowledgeBaseForCustom(paramsForCustom);
        }

        PageRowBounds pageRowBounds = new PageRowBounds(listKnowledgeBaseQo.getOffset(),
            listKnowledgeBaseQo.getLimit());
        String realQueryName = SqlLikeEscapeHelper.escapeLikeCharacters(listKnowledgeBaseQo.getName());
        List<KnowledgeBaseEntity> items;
        if (StringUtils.isNotEmpty(listKnowledgeBaseQo.getShareType())) {
            items = queryKnowledgeBaseByShareType(projectId, pageRowBounds, realQueryName, listKnowledgeBaseQo);
        } else {
            String shareScope = listKnowledgeBaseQo.getShareScope();
            if (ShareScopeEnum.GLOBAL.equals(ShareScopeEnum.fromValue(shareScope))) {
                items = knowledgeBaseMapper.queryKnowledgeBaseListByShareScope(projectId, realQueryName, null,
                    listKnowledgeBaseQo.getType(), listKnowledgeBaseQo.getStatus(), ShareScopeEnum.GLOBAL.name(),
                    listKnowledgeBaseQo.getKnowledgeBaseConnectionId(), null, listKnowledgeBaseQo.getKnowledgeBaseIds(),
                    pageRowBounds);
            } else if (ShareScopeEnum.ALL.equals(ShareScopeEnum.fromValue(shareScope))) {
                items = knowledgeBaseMapper.queryKnowledgeBaseListFromGlobalAndSelf(projectId,
                    listKnowledgeBaseQo.getWorkspaceId(), realQueryName, null, listKnowledgeBaseQo.getType(),
                    listKnowledgeBaseQo.getStatus(), listKnowledgeBaseQo.getKnowledgeBaseConnectionId(), null,
                    listKnowledgeBaseQo.getKnowledgeBaseIds(), pageRowBounds);
            } else {
                items = knowledgeBaseMapper.queryKnowledgeBaseList(projectId, listKnowledgeBaseQo.getWorkspaceId(),
                    listKnowledgeBaseQo.getShareScope(), realQueryName, null, listKnowledgeBaseQo.getType(),
                    listKnowledgeBaseQo.getStatus(), listKnowledgeBaseQo.getKnowledgeBaseConnectionId(), null,
                    listKnowledgeBaseQo.getKnowledgeBaseIds(), pageRowBounds);
            }
        }
        List<String> connectionIds = items.stream()
            .map(KnowledgeBaseEntity::getKnowledgeBaseConnectionId)
            .filter(StringUtils::isNotEmpty)
            .toList();
        final Map<String, KnowledgeBaseConnection> connectionMap = Maps.newHashMap();
        if (CollectionUtils.isNotEmpty(connectionIds)) {
            List<KnowledgeBaseConnection> connections
                = knowledgeBaseConnectionMapper.batchQueryKnowledgeBaseConnections(connectionIds, null);
            connectionMap.putAll(
                connections.stream().collect(Collectors.toMap(KnowledgeBaseConnection::getId, item -> item)));
        }
        List<KnowledgeBaseListItem> resultList = ObjectUtils.firstNonNull(items,
                Collections.<KnowledgeBaseEntity>emptyList())
            .stream()
            .map(item -> new KnowledgeBaseListItem().setKnowledgeBaseId(item.getId())
                .setType(KnowledgeBaseListItem.TypeEnum.fromValue(item.getType()))
                .setName(item.getName())
                .setIcon(item.getIcon())
                .setDescription(item.getDescription())
                .setRepoType(KnowledgeBaseListItem.RepoTypeEnum.fromValue(item.getRepoType()) == null
                    ? KnowledgeBaseListItem.RepoTypeEnum.EXCLUSIVE
                    : KnowledgeBaseListItem.RepoTypeEnum.fromValue(item.getRepoType()))
                .setStatus(KnowledgeBaseListItem.StatusEnum.fromValue(item.getStatus()))
                // 对于第三方知识库，需要额外补充知识源和前台页面跳转地址
                .setSource(convertConnectionToSource(item, connectionMap.get(item.getKnowledgeBaseConnectionId())))
                .setWorkspaceId(item.getWorkspaceId())
                .setKnowledgeBaseConnectionId(item.getKnowledgeBaseConnectionId())
                .setCreatedUserId(item.getCreatedUserId())
                .setCreatedUserName(item.getCreatedUserName())
                .setCreateTime(item.getCreateTime())
                .setLastUpdateUserId(item.getLastUpdateUserId())
                .setLastUpdateUserName(item.getLastUpdateUserName())
                .setUpdateTime(item.getUpdateTime())
                .setShareScope(KnowledgeBaseListItem.ShareScopeEnum.fromValue(item.getShareScope())))
            .toList();
        ListKnowledgeBasesResponseBody response = new ListKnowledgeBasesResponseBody();
        response.setTotal(pageRowBounds.getTotal());
        response.setItems(resultList);
        return response;
    }

    private List<KnowledgeBaseEntity> queryKnowledgeBaseByShareType(String projectId, PageRowBounds pageRowBounds,
        String realQueryName, ListKnowledgeBasesQo listKnowledgeBaseQo) {
        String shareType = listKnowledgeBaseQo.getShareType();
        List<ShareScopeEnum> shareScopeEnums = new ArrayList<>();
        shareScopeEnums.add(ShareScopeEnum.GLOBAL);
        shareScopeEnums.add(ShareScopeEnum.PARTIAL);
        List<KnowledgeBaseEntity> items = List.of();
        if (OTHER_SHARED.equals(shareType)) {
            items = knowledgeBaseMapper.queryOtherSharedKnowledgeBaseList(projectId,
                listKnowledgeBaseQo.getWorkspaceId(), realQueryName, shareScopeEnums, listKnowledgeBaseQo.getType(),
                listKnowledgeBaseQo.getStatus(), listKnowledgeBaseQo.getKnowledgeBaseConnectionId(),
                listKnowledgeBaseQo.getKnowledgeBaseIds(), pageRowBounds);
        }
        if (MY_SHARED.equals(shareType)) {
            items = knowledgeBaseMapper.queryMySharedKnowledgeBaseList(projectId, listKnowledgeBaseQo.getWorkspaceId(),
                realQueryName, shareScopeEnums, listKnowledgeBaseQo.getType(), listKnowledgeBaseQo.getStatus(),
                listKnowledgeBaseQo.getKnowledgeBaseConnectionId(), listKnowledgeBaseQo.getKnowledgeBaseIds(),
                pageRowBounds);
        }
        return items;
    }

    /**
     * 查询知识库列表（直接从知识库系统里查询知识库列表）
     *
     * @param body
     * @return
     */
    private ListKnowledgeBasesResponseBody listKnowledgeBaseForCustom(ListKnowledgeBaseParamsForCustom body) {
        if (CollectionUtils.isNotEmpty(body.getKnowledgeBaseIds())) {
            return batchQueryKnowledgeBaseForCustom(body);
        }
        // 单纯查询列表时，直接调用列表查询接口进行查询
        ListKnowledgeRepoResp knowledgeRepoResp = knowledgeRepoContext.getService(knowledgeSource)
            .listKnowledgeRepos(new ListKnowledgeRepoReq().setName(body.getName())
                .setPageNum(body.getOffset() / body.getLimit() + 1)
                .setPageSize(body.getLimit())
                .setKnowledgeBaseType(body.getKnowledgeBaseType()));
        log.info("list knowledge for CUSTOM response is :{}", JacksonUtils.toJson(knowledgeRepoResp));
        if (Objects.isNull(knowledgeRepoResp.getDataList())) {
            return new ListKnowledgeBasesResponseBody().setTotal(0L).setItems(Collections.emptyList());
        }
        ListKnowledgeBasesResponseBody response = new ListKnowledgeBasesResponseBody();
        response.setTotal(knowledgeRepoResp.getTotal());
        response.setItems(Lists.newArrayList());
        for (KnowledgeRepoInfo knowledgeRepoInfo : knowledgeRepoResp.getDataList()) {
            response.getItems().add(buildCustomKnowledgeBaseItem(knowledgeRepoInfo));
        }
        return response;
    }

    /**
     * CUSTOM 场景下，将 LakeSearch 返回的 KnowledgeRepoInfo 构建为完整的 KnowledgeBaseListItem。
     * 列表查询与按 ids 批量查询共用，保证两条路径返回的字段一致（含 description/icon 等），
     * 避免前端按 ids 回查详情时拿到的精简对象覆盖掉已有的描述等字段。
     */
    private KnowledgeBaseListItem buildCustomKnowledgeBaseItem(KnowledgeRepoInfo knowledgeRepoInfo) {
        KnowledgeBaseListItem knowledgeBase = new KnowledgeBaseListItem();
        knowledgeBase.setName(knowledgeRepoInfo.getName());
        KnowledgeBaseListItem.StatusEnum statusEnum = KnowledgeBaseListItem.StatusEnum.fromValue(
            knowledgeRepoInfo.getStatus());
        knowledgeBase.setStatus(Objects.requireNonNullElse(statusEnum, KnowledgeBaseListItem.StatusEnum.OPEN));
        knowledgeBase.setRepoType(KnowledgeBaseListItem.RepoTypeEnum.EXCLUSIVE);
        knowledgeBase.setKnowledgeBaseId(knowledgeRepoInfo.getId());
        knowledgeBase.setDescription(knowledgeRepoInfo.getDetail());
        knowledgeBase.setIcon(defaultIcon);
        knowledgeBase.setLastUpdateUserId(RequestContextUtils.getRequestUserId());
        knowledgeBase.setLastUpdateUserName(RequestContextUtils.getRequestUserName());
        knowledgeBase.setCreateTime(convertTimeForCustom(knowledgeRepoInfo.getCreateTime()));
        knowledgeBase.setUpdateTime(convertTimeForCustom(knowledgeRepoInfo.getUpdateTime()));
        knowledgeBase.setType(KnowledgeBaseListItem.TypeEnum.INTERNAL);
        return knowledgeBase;
    }

    /**
     * CUSTOM场景下，批量查询知识库详情
     *
     * @param body
     * @return
     */
    private ListKnowledgeBasesResponseBody batchQueryKnowledgeBaseForCustom(ListKnowledgeBaseParamsForCustom body) {
        int batchQuerySize = 200;
        int pageNum = 1;
        List<KnowledgeRepoInfo> allKnowledgeBases = new ArrayList<>();
        Map<String, KnowledgeRepoInfo> knowledgeBaseToReturn = Maps.newHashMap();
        Set<String> knowledgeBaseIds = new HashSet<>(body.getKnowledgeBaseIds());
        long total = 0;
        while (true) {
            ListKnowledgeRepoResp knowledgeRepoResp = knowledgeRepoContext.getService(knowledgeSource)
                .listKnowledgeRepos(
                    new ListKnowledgeRepoReq().setName(body.getName()).setPageNum(pageNum).setPageSize(batchQuerySize)
                        .setKnowledgeBaseType(body.getKnowledgeBaseType()));
            total = knowledgeRepoResp.getTotal();
            Map<String, KnowledgeRepoInfo> knowledgeMap = ObjectUtils.firstNonNull(knowledgeRepoResp.getDataList(),
                    Collections.<KnowledgeRepoInfo>emptyList())
                .stream()
                .filter(item -> knowledgeBaseIds.contains(item.getId()))
                .collect(Collectors.toMap(KnowledgeRepoInfo::getId, Function.identity()));
            knowledgeBaseToReturn.putAll(knowledgeMap);
            allKnowledgeBases.addAll(knowledgeRepoResp.getDataList());
            // 如果提前把待查询的知识库查询完了，中断循环，可以少查几次，否则需要一直查询直到把所有的知识库查完
            if (knowledgeBaseIds.size() == knowledgeBaseToReturn.size()) {
                break;
            }
            pageNum++;
            if (allKnowledgeBases.size() >= total || CollectionUtils.isEmpty(knowledgeRepoResp.getDataList())) {
                break;
            }
        }
        ListKnowledgeBasesResponseBody response = new ListKnowledgeBasesResponseBody();
        response.setTotal((long) knowledgeBaseToReturn.size());
        response.setItems(knowledgeBaseToReturn.values()
            .stream()
            .map(item -> buildCustomKnowledgeBaseItem(item))
            .toList());
        return response;
    }

    /**
     * 调用的知识库系统接口中的时间做处理
     *
     * @param timeStr
     * @return
     */
    private Long convertTimeForCustom(String timeStr) {
        if (StringUtils.isEmpty(timeStr)) {
            return null;
        }
        try {
            // 此处暂时参考KooSearch的接口定义，知识库的创建时间和修改时间都是时间戳格式的字符串，因此此处直接转成Long格式返回
            return Long.valueOf(timeStr);
        } catch (Exception e) {
            log.error("Convert time to timestamp error for custom:{}", timeStr);
            return null;
        }
    }

    /**
     * 查询某个三方知识库中所有的知识库
     *
     * @param connectorDefinition
     * @return
     */
    private List<ExternalKnowledgeBaseInfo> queryAllExternalKnowledgeBases(ConnectorDefinition connectorDefinition) {
        int offset = 0;
        int limit = 100;
        PageResult<ExternalKnowledgeBaseInfo> pageResult = knowledgeBaseConnectorContext.listKnowledgeBase(null, offset,
            limit, connectorDefinition, RequestContextUtils.getRequestAuthToken());
        List<ExternalKnowledgeBaseInfo> allKnowledgeBase = new ArrayList<>(pageResult.getItems());
        offset += limit;
        while (allKnowledgeBase.size() < pageResult.getTotalCount()) {
            pageResult = knowledgeBaseConnectorContext.listKnowledgeBase(null, offset, limit, connectorDefinition,
                RequestContextUtils.getRequestAuthToken());
            allKnowledgeBase.addAll(pageResult.getItems());
            offset += limit;
        }
        return allKnowledgeBase;
    }

    /**
     * 根据连接ID找到对应的连接信息
     *
     * @param connectionId
     * @param workSpaceId
     * @return
     */
    private ConnectorDefinition getConnectionDefinition(String connectionId, String workSpaceId) {
        List<KnowledgeBaseConnection> connections = knowledgeBaseConnectionMapper.batchQueryKnowledgeBaseConnections(
            Lists.newArrayList(connectionId), workSpaceId);
        if (CollectionUtils.isEmpty(connections)) {
            log.warn("can not find third part connection for connectionId:{} in workspace {}", connectionId,
                workSpaceId);
            throw new AgentBaseException(ErrorCode.THIRD_PARTY_KNOWLEDGE_CONNECTION_NOT_EXISTS, connectionId);
        }
        KnowledgeBaseConnectorEntity connector = knowledgeBaseConnectorMapper.find(connections.get(0).getConnectorId());
        ConnectorDefinition connectorDefinition = convertConnectionToDefinition(connections.get(0));
        Map<String, KnowledgeBaseConnectorParam> paramMap = connector.getParams()
            .stream()
            .collect(Collectors.toMap(KnowledgeBaseConnectorParam::getCode, item -> item));
        connectorDefinition.getParamDefinitions().forEach(param -> {
            if (paramMap.containsKey(param.getCode())) {
                param.setType(ConnectionParamType.valueOf(paramMap.get(param.getCode()).getType().toString()));
            }
        });
        return connectorDefinition;
    }

    private ExternalKnowledgeBaseSource convertConnectionToSource(KnowledgeBaseEntity knowledgeBase,
        KnowledgeBaseConnection connection) {
        if (StringUtils.isEmpty(knowledgeBase.getKnowledgeBaseConnectionId()) || ObjectUtils.isEmpty(connection)) {
            log.info("knowledgeBaseConnectionId is empty or connection is empty, knowledgeBaseId:{} ",
                knowledgeBase.getKnowledgeBaseConnectionId());
            return null;
        }
        ExternalKnowledgeBaseSource source = new ExternalKnowledgeBaseSource();
        source.setKnowledgeBaseConnectorId(connection.getConnectorId());
        source.setKnowledgeBaseConnectionId(knowledgeBase.getKnowledgeBaseConnectionId());
        source.setKnowledgeBaseConnectionName(connection.getName());
        source.setDetailPageUrl(getDetailPagePath(knowledgeBase, convertConnectionToDefinition(connection)));
        return source;
    }

    private ConnectorDefinition convertConnectionToDefinition(KnowledgeBaseConnection connection) {
        if (Objects.isNull(connection)) {
            return null;
        }
        List<ConnectorParamDefinition> params = JacksonUtils.readValue(connection.getParams(),
            new TypeReference<List<ConnectorParamDefinition>>() { });
        return ConnectorDefinition.builder()
            .code(connection.getConnectorId())
            .connectionId(connection.getId())
            .domainId(connection.getDomainId())
            .paramDefinitions(params)
            .build();
    }

    private String getDetailPagePath(KnowledgeBaseEntity knowledgeBase, ConnectorDefinition connectorDefinition) {
        if (connectorDefinition == null || CollectionUtils.isEmpty(connectorDefinition.getParamDefinitions())) {
            return null;
        }
        String detailPagePath = StringUtils.EMPTY;
        for (ConnectorParamDefinition paramDefinition : connectorDefinition.getParamDefinitions()) {
            if (Strings.CS.equals(ConnectorParamConstants.DETAIL_PAGE_PARAM, paramDefinition.getCode())) {
                detailPagePath = paramDefinition.getValue();
            }
        }
        return ConnectorParamUtil.getDetailPageUrl(knowledgeBase.getExternalId(), detailPagePath);
    }

    public boolean isExistedKnowledgeBase(String knowledgeRepoId, String workspaceId) {
        KnowledgeBaseEntity knowledgeBase = knowledgeBaseMapper.selectByIdAndWorkspaceId(workspaceId, knowledgeRepoId);
        return Objects.nonNull(knowledgeBase);
    }

}

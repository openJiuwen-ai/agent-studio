/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.environment;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.huaweicloud.sdk.vpc.v2.model.ListSubnetsResponse;
import com.huaweicloud.sdk.vpc.v2.model.ShowSubnetResponse;
import com.huaweicloud.sdk.vpc.v2.model.Subnet;
import com.huaweicloud.sdk.vpc.v3.model.ListVpcsResponse;
import com.huaweicloud.sdk.vpc.v3.model.ShowVpcResponse;
import com.huaweicloud.sdk.vpc.v3.model.Vpc;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.FileCommonUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.*;
import com.openjiuwen.studio.agent.manager.entity.*;
import com.openjiuwen.studio.agent.manager.enums.EnumEnvStatus;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentVariableMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.service.EnvironmentClientService;
import com.openjiuwen.studio.agent.manager.service.IEnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.environment.model.*;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.IamServiceUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import jakarta.annotation.PostConstruct;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.ObjectUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import static com.openjiuwen.studio.agent.common.enums.StudioError.*;
import static com.openjiuwen.studio.agent.manager.enums.EnumEnvStatus.*;

/**
 * 功能描述
 *
 */
@Slf4j
@Service
public class EnvironmentServiceManagerService implements IEnvironmentServiceManagerService {

    @Value("${env.type}")
    private String envType;

    /**
     * 同步环境状态线程最大休眠时间
     */
    private static final int SYNC_STATUS_THREAD_MAX_SLEEP_TIME = 1000;

    /**
     * 单页显示的最大条数
     */
    private static final int PAGE_MAX_LIMIT = 100;

    /**
     * 单页默认显示最小条数
     */
    private static final int PAGE_MIN_LIMIT = 10;

    private static final String FAIL = "fail";

    private static final String SUCCESS = "success";

    /**
     * 环境名常量
     */
    private static final String ENV_NAME = "name";

    /**
     * 密码隐藏符合
     */
    private static final String PASSWORD_PLACEHOLDER = "******";

    /**
     * 导入的环境变量文件类型
     */
    private static final String IMPORT_ENV_FILE_TYPE = ".jsonl";

    /**
     * 工作流中引用的环境正则校验
     */
    private static final Pattern ENVIRONMENT_NAME_IN_WORKFLOW_REGEX = Pattern.compile("^\\{name=");

    /**
     * 消息队列
     */
    private GlobalSyncAgentOpsStatus<String> syncCaeStatusQueue;

    @Autowired
    private EnvironmentClientService environmentClientService;

    @Autowired
    private IamServiceUtils iamServiceUtils;

    @Autowired
    private EnvironmentCacheUtil environmentCacheUtil;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private EnvironmentManagerMapper environmentManagerMapper;

    @Autowired
    private EnvironmentVariableMapper environmentVariableMapper;

    @Value("${env-management.limit-quota:5}")
    private int environmentQuota;

    @Value("${env-management.variables.limit-quota:1000}")
    private int environmentVariablesQuota;

    private final Object lock = new Object();

    @Value("${env-management.ops-call:true}")
    private boolean opsCallSwitch;

    @Value("${env-management.domain-verification-ima5:false}")
    private boolean mainAccountVerification;

    @Value("${env-management.variables.max-upload-file-size-kb:10240}")
    private long fileMaxSize;

    /**
     * 初始化方法
     *
     */
    @PostConstruct
    public void init() {
        syncCaeStatusQueue = GlobalSyncAgentOpsStatus.getInstance();
        syncCaeStatusQueue.setDataProcessor(this::synchronizationCaeStatus);
        syncCaeStatusQueue.start();
    }

    /**
     * 同步环境状态
     *
     */
    public void synchronizationCaeStatus(String id) {
        log.info("Start sync env status from AgentOps; {}", id);
        if (StringUtils.isBlank(id)) {
            return;
        }
        try {
            EnvironmentManagerEntity envInfo = environmentManagerMapper.findById(id);
            if (envInfo == null) {
                return;
            }
            if (!Strings.CI.equals(envInfo.getStatus(), CREATING.getValue())
                && !Strings.CI.equals(envInfo.getStatus(), EnumEnvStatus.DELETING.getValue())
                && !Strings.CI.equals(envInfo.getStatus(), EnumEnvStatus.UPDATING.getValue())) {
                return;
            }
            OpsEnvironmentInfo opsEnvironmentInfo = this.environmentClientService.queryEnvironmentInfo(
                envInfo.getProjectId(), envInfo.getId(), envInfo.getDomainId(), envInfo.getStatus());
            if (opsEnvironmentInfo == null) {
                return;
            }
            EnumEnvStatus opsEnvStatus = EnumEnvStatus.fromStatus(opsEnvironmentInfo.getStatus());
            if (opsEnvStatus == null) {
                return;
            }
            if (opsEnvStatus == CREATING || opsEnvStatus == DELETING || opsEnvStatus == UPDATING) {
                syncCaeStatusQueue.addData(id);
                Thread.sleep(SYNC_STATUS_THREAD_MAX_SLEEP_TIME);
                return;
            }
            if (opsEnvStatus == DELETED || opsEnvStatus == NOT_FOUND) {
                environmentManagerMapper.deleteById(envInfo.getId());
                return;
            }
            environmentManagerMapper.updateStatusById(id, opsEnvStatus.getValue(), null);

            // 首个环境设置为默认
            if (opsEnvStatus == READY) {
                List<EnvironmentManagerEntity> environmentManagerEntities
                    = environmentManagerMapper.findByProjectIdAndIsDefaultTrue(envInfo.getProjectId());
                if (CollectionUtils.isEmpty(environmentManagerEntities)) {
                    int result = environmentManagerMapper.updateIsDefaultById(envInfo.getId(),
                        true, null);
                    if (result > 0) {
                        environmentCacheUtil.updateDefaultEnvironmentCache(envInfo.getProjectId(), envInfo.getId());
                    }
                }
            }
        } catch (Exception exception) {
            syncCaeStatusQueue.addData(id);
            try {
                Thread.sleep(SYNC_STATUS_THREAD_MAX_SLEEP_TIME);
            } catch (InterruptedException e) {
                log.error("Sync env status interrupted", e);
            }
            log.error("Sync env status ", exception);
        } finally {
            log.info("Finish sync env status from AgentOps; id {}; queue size is {}",
                id, syncCaeStatusQueue.size());
        }
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Environment",
        description = "创建环境",
        resourceId = "-1",
        resourceName = "body.name"
    )
    public String createEnvironmentInfo(String projectId, EnvironmentInfoRequest body) {
        if (body == null) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL);
        }
        checkEnvName(body.getName(), projectId);
        Vpc vpcInfo = this.checkVpc(body.getVpcId());
        Subnet subnetInfo = this.checkSubnet(body.getSubnetId());
        CreateEnvOpsMetaData opsMetaData = this.buildCaeMetaData(vpcInfo, subnetInfo,
            Map.of(ENV_NAME, body.getName(), "desc", body.getDescription() == null ? "" : body.getDescription()));
        EnvironmentManagerResources managerResources = EnvironmentManagerResources.builder()
            .opsMetadata(opsMetaData == null ? new CreateEnvOpsMetaData() : opsMetaData)
            .vpcName(vpcInfo.getName())
            .vpcCidr(vpcInfo.getCidr())
            .subnetName(subnetInfo.getName())
            .subnetCidr(subnetInfo.getCidr())
            .build();
        synchronized (lock) {
            validationQuota(projectId);
            String opsEnvId = this.environmentClientService.createEnvironment(projectId, opsMetaData);
            EnvironmentManagerEntity entity = new EnvironmentManagerEntity();
            entity.setId(opsEnvId);
            if (StringUtils.isNotBlank(body.getId())) {
                entity.setId(body.getId());
            }
            entity.setName(body.getName());
            entity.setIsDefault(false);
            entity.setCreatorId(RequestContextUtils.getRequestUserId());
            entity.setStatus(CREATING.getValue());
            managerResources.getOpsMetadata().setDescription("");
            entity.setResources(JSONObject.toJSONString(managerResources));
            entity.setProjectId(RequestContextUtils.getRequestProjectId());
            entity.setUpdaterId(RequestContextUtils.getRequestUserId());
            entity.setDescription(body.getDescription());
            entity.setDomainId(RequestContextUtils.getRequestUserDomainId());
            entity.setCreatedOn(new Date());
            entity.setUpdatedOn(new Date());
            try {
                log.info("entity:{}",entity);
                environmentManagerMapper.insert(entity);
                this.syncCaeStatusQueue.addData(entity.getId());
                return entity.getId();
            } catch (Exception e) {
                throw new AgentStudioException(ENVIRONMENT_CREATE_FAIL);
            }
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Environment",
        description = "删除环境",
        resourceId = "environmentId",
        resourceName = ""
    )
    public Boolean deleteEnvironment(String projectId, String environmentId) {
        EnvironmentManagerEntity envInfo = environmentManagerMapper.findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        EnumEnvStatus status = EnumEnvStatus.fromStatus(envInfo.getStatus());
        if (status == CREATING || status == DELETING) {
            log.error("The current status does not support deletion, status {}", envInfo.getStatus());
            throw new AgentStudioException(ENVIRONMENT_DELETE_NOT_SUPPORT);
        }
        this.environmentClientService.hasDeleteEnvironment(projectId, envInfo.getId());
        try {
            environmentManagerMapper.updateStatusAndIsDefaultById(environmentId, DELETING.getValue(),
                CommonUtil.getUserId(), false);
            this.deleteAllEnvironmentVariables(projectId, environmentId);
            this.syncCaeStatusQueue.addData(envInfo.getId());
            if (!envInfo.getIsDefault()) {
                return true;
            }
            List<EnvironmentManagerEntity> isDefaultFase
                = environmentManagerMapper.findByProjectIdAndIsDefaultFalseAndStatus(projectId, READY.getValue());
            if (CollectionUtils.isEmpty(isDefaultFase)) {
                // 项目环境全部删除，清除默认环境缓存
                environmentCacheUtil.deleteDefaultEnvironmentCache(projectId);
                return true;
            }
            environmentManagerMapper.updateIsDefaultById(isDefaultFase.get(0).getId(),
                true, CommonUtil.getUserId());
            environmentCacheUtil.updateDefaultEnvironmentCache(projectId, isDefaultFase.get(0).getId());
            return true;
        } catch (Exception e) {
            throw new AgentStudioException(ENVIRONMENT_DELETE_FAIL);
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Environment",
        description = "设置默认环境",
        resourceId = "environmentId",
        resourceName = ""
    )
    public Boolean isDefaultEnvironments(String projectId, String environmentId) {
        EnvironmentManagerEntity envInfo = environmentManagerMapper.findByIdAndProjectId(environmentId,
            projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        if (EnumEnvStatus.fromStatus(envInfo.getStatus()) != EnumEnvStatus.READY) {
            throw new AgentStudioException(ENVIRONMENT_DEFAULT_NOT_SUPPORT);
        }
        List<EnvironmentManagerEntity> environmentManagerEntities
            = environmentManagerMapper.findByProjectIdAndIsDefaultTrue(projectId);
        if (!CollectionUtils.isEmpty(environmentManagerEntities)) {
            List<String> envIds = environmentManagerEntities.stream().map(EnvironmentManagerEntity::getId).toList();
            environmentManagerMapper.batchUpdateIsDefaultByIds(envIds,
                false, RequestContextUtils.getRequestUserId());
        }
        int result = environmentManagerMapper.updateIsDefaultById(environmentId,
            true, RequestContextUtils.getRequestUserId());
        if (result <= 0) {
            throw new AgentStudioException(ENVIRONMENT_DEFAULT_SET_FAIL);
        }
        // 同步项目默认环境缓存，runtime 直连时按 project_id 读取
        environmentCacheUtil.updateDefaultEnvironmentCache(projectId, environmentId);
        return true;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Environment",
        description = "修改环境",
        resourceId = "environmentId",
        resourceName = "body.description"
    )
    public Boolean modifyEnvironmentInfo(String projectId, String environmentId,
        ModifyEnvironmentInfoRequestBody body) {
        log.info("projectId={},userId={}",RequestContextUtils.getRequestProjectId(),RequestContextUtils.getRequestUserId());
        EnvironmentManagerEntity envInfo = environmentManagerMapper
            .findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        if (EnumEnvStatus.fromStatus(envInfo.getStatus()) != EnumEnvStatus.READY) {
            throw new AgentStudioException(ENVIRONMENT_DEFAULT_NOT_SUPPORT);
        }
        envInfo.setDescription(body.getDescription());
        envInfo.setUpdaterId(RequestContextUtils.getRequestUserId());
        envInfo.setUpdatedOn(new Date());
        try {
            environmentManagerMapper.updateById(envInfo);
            return true;
        } catch (Exception e) {
            throw new AgentStudioException(ENVIRONMENT_MODIFY_FAIL);
        }
    }

    @Override
    public Environment queryEnvironment(String projectId, String environmentId) {
        EnvironmentManagerEntity envInfo = environmentManagerMapper
            .findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        Environment environment = new Environment();
        BeanUtils.copyProperties(envInfo, environment);
        environment.setCreatedOn(envInfo.getCreatedOn().getTime());
        environment.setUpdatedOn(envInfo.getUpdatedOn().getTime());
        EnvironmentManagerResources envMetaData = JSONObject.parseObject(
            envInfo.getResources(), EnvironmentManagerResources.class);
        if (envMetaData != null) {
            environment.setVpcName(envMetaData.getVpcName());
            environment.setVpcCidr(envMetaData.getVpcCidr());
            environment.setSubnetName(envMetaData.getSubnetName());
            environment.setSubnetCidr(envMetaData.getSubnetCidr());
        }
        OpsEnvironmentInfo opsEnvironmentInfo
            = this.environmentClientService.queryEnvironmentInfo(envInfo.getProjectId(), envInfo.getId(), RequestContextUtils.getRequestUserDomainId(), null);
        if (opsEnvironmentInfo == null) {
            return environment;
        }
        environment.setVpcEp(opsEnvironmentInfo.getVpcEp());
        environment.setEip(opsEnvironmentInfo.getEip());
        return environment;
    }

    private EnvironmentManagerEntity queryEnvironmentDetail(String projectId, String environmentId) {
        EnvironmentManagerEntity entity = environmentManagerMapper.findByIdAndProjectId(environmentId, projectId);
        if (ObjectUtils.isEmpty(entity)) {
            log.info("Environment not found, environmentId: {}, projectId: {}", environmentId, projectId);
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        return entity;
    }

    @Override
    public EnvironmentInstances queryEnvironmentInstances(String projectId,
        String environmentId, QueryEnvironmentInstancesQo queryEnvironmentInstancesQo) {
        EnvironmentManagerEntity envInfo = environmentManagerMapper
            .findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        OpsEnvironmentInstances opsEnvironmentInstances = this.environmentClientService.queryEnvironmentInstance(
            projectId, envInfo.getId(), queryEnvironmentInstancesQo.getPageNo(),
            queryEnvironmentInstancesQo.getPageSize());
        List<String> workspaceIds = opsEnvironmentInstances.getItems().stream().map(OpsEnvironmentInstance::getWorkspaceId).toList();
        Map<String, String> workspaceIdRelName;
        if (!CollectionUtils.isEmpty(workspaceIds)) {
            List<WorkspaceEntity> workspaceEntities = this.workspaceMapper.selectWorkspaceByWorkspaceIdList(
                workspaceIds);
            workspaceIdRelName = workspaceEntities.stream()
                .collect(Collectors.toMap(WorkspaceEntity::getId, WorkspaceEntity::getName));
        } else {
            workspaceIdRelName = new HashMap<>();
        }
        List<EnvironmentInstance> envInstances = opsEnvironmentInstances.getItems().stream().map(instance -> {
            EnvironmentInstance environmentInstance = new EnvironmentInstance();
            environmentInstance.setAgentName(instance.getAgentName());
            environmentInstance.setDeployName(instance.getDeployName());
            environmentInstance.setStatus(instance.getStatus());
            environmentInstance.setVersion(instance.getAgentVersion());
            environmentInstance.setAgentType(instance.getAgentType());
            environmentInstance.setWorkspaceName(workspaceIdRelName.get(instance.getWorkspaceId()) == null ? "" : workspaceIdRelName.get(instance.getWorkspaceId()));
            return environmentInstance;
        }).toList();
        EnvironmentInstances environmentInstances = new EnvironmentInstances();
        environmentInstances.setEnvInfo(envInstances);
        environmentInstances.setTotal(opsEnvironmentInstances.getTotal());
        return environmentInstances;
    }

    @Override
    public Environments queryEnvironmentsList(String projectId, QueryEnvironmentsListQo queryEnvironmentsListQo) {
        int limit = queryEnvironmentsListQo.getLimit();
        if (limit > PAGE_MAX_LIMIT) {
            limit = PAGE_MIN_LIMIT;
        }
        int offset = queryEnvironmentsListQo.getOffset();
        if (offset < 0) {
            offset = 0;
        }
        String name = queryEnvironmentsListQo.getName();
        List<EnvironmentManagerEntity> environmentManagerEntities;
        if (Boolean.TRUE.equals(queryEnvironmentsListQo.getIsDefault())) {
            // 按默认环境过滤：与运行时默认环境兜底解析（AgentServiceProxyService.resolveEnvironmentId
            // 走的 findByProjectIdAndIsDefaultTrue）同源，前端据此判断"是否存在默认环境"时
            // 不受分页截断影响（列表按 created_on 倒序分页，默认环境可能不在第一页）；
            // 默认环境项目内唯一，忽略 offset/limit
            environmentManagerEntities = environmentManagerMapper.findByProjectIdAndIsDefaultTrue(projectId);
        } else {
            environmentManagerEntities = environmentManagerMapper.selectByConditionWithPage(name, projectId, offset, limit);
        }
        List<Environment> envInfoList = null;
        if (!environmentManagerEntities.isEmpty()) {
            envInfoList = environmentManagerEntities.stream().map(entity -> {
                Environment environment = new Environment();
                BeanUtils.copyProperties(entity, environment);
                environment.setCreatedOn(entity.getCreatedOn().getTime());
                environment.setUpdatedOn(entity.getUpdatedOn().getTime());
                environment.setIsDefault(entity.getIsDefault());
                if (StringUtils.isNotBlank(entity.getResources())) {
                    EnvironmentManagerResources managerResources = JSONObject.parseObject(entity.getResources(),
                        EnvironmentManagerResources.class);
                    environment.setVpcName(managerResources == null ? "" : managerResources.getVpcName());
                    environment.setSubnetCidr(managerResources == null ? "" : managerResources.getSubnetCidr());
                }
                if (Strings.CI.equals(entity.getStatus(), CREATING.getValue())
                    || Strings.CI.equals(entity.getStatus(), DELETING.getValue())
                    || Strings.CI.equals(entity.getStatus(), UPDATING.getValue())) {
                    this.syncCaeStatusQueue.addData(entity.getId());
                }
                if (Strings.CI.equals(entity.getStatus(), FAILED.getValue())
                    || Strings.CI.equals(entity.getStatus(), DELETE_FAILED.getValue())) {
                   try {
                       OpsEnvironmentInfo opsEnvironmentInfo
                           = this.environmentClientService.queryEnvironmentInfo(entity.getProjectId(), entity.getId(), RequestContextUtils.getRequestUserDomainId(), null);
                       if (opsEnvironmentInfo != null) {
                           environment.setStatusReason(opsEnvironmentInfo.getStatusReason());
                       }
                   } catch (AgentStudioException e) {
                       log.error("Reason for failed environment query exception", e);
                   }
                }
                return environment;
            }).toList();
        }
        Environments environments = new Environments();
        if (Boolean.TRUE.equals(queryEnvironmentsListQo.getIsDefault())) {
            // 默认环境单条返回，total 即 0/1
            environments.setTotal(environmentManagerEntities.size());
        } else {
            environments.setTotal(environmentManagerMapper.countByCondition(name, projectId));
        }
        environments.setEnvInfo(envInfoList);
        return environments;
    }

    @Override
    public EnvironmentVariablesResp queryEnvironmentVariables(String projectId,
        QueryEnvironmentVariablesQo queryEnvironmentVariablesQo) {
        int limit = queryEnvironmentVariablesQo.getLimit();
        if (limit > PAGE_MAX_LIMIT) {
            limit = PAGE_MIN_LIMIT;
        }
        int offset = queryEnvironmentVariablesQo.getOffset();
        if (offset < 0 || offset > 1000) {
            offset = 0;
        }
        int pageNum = offset / limit;
        List<EnvironmentManagerEntity> environmentManagerEntities = environmentManagerMapper.selectAllByStatus(READY.getValue(), projectId, offset, limit);

        List<EnvironmentVariableResp> environmentVariablesList = new ArrayList<>();
        if (!environmentManagerEntities.isEmpty()) {
            environmentVariablesList = environmentManagerEntities.stream().map(env -> {
                EnvironmentVariableEntity environmentVariableFromDb
                    = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId,
                    queryEnvironmentVariablesQo.getWorkspaceId(), env.getId());
                EnvironmentVariableResp environmentVariableResp = new EnvironmentVariableResp();
                environmentVariableResp.setId(env.getId());
                environmentVariableResp.setName(env.getName());
                environmentVariableResp.setEnvDescription(env.getDescription());
                if (environmentVariableFromDb == null) {
                    environmentVariableResp.setCount(0);
                    environmentVariableResp.setVariables(new ArrayList<>());
                    return environmentVariableResp;
                }
                List<EnvironmentVariable> environmentVariables = JsonUtils.json2Array(environmentVariableFromDb.getEnvVariable(), EnvironmentVariable.class);
                if (!CollectionUtils.isEmpty(environmentVariables)) {
                    environmentVariables.forEach(variable -> {
                        if (variable.getValue() != null && variable.getValue().isSecret()) {
                            variable.getValue().setContent(PASSWORD_PLACEHOLDER);
                        }
                    });
                }
                environmentVariableResp.setCount(environmentVariables == null ? 0 : environmentVariables.size());
                environmentVariableResp.setVariables(environmentVariables);

                // 异步同步缓存信息
                CompletableFuture.runAsync(() -> {
                    boolean isExistEnvironmentVariableCache = this.environmentCacheUtil.isExistEnvironmentVariableCache(
                        env.getId(), environmentVariableFromDb.getWorkspaceId());
                    if (!isExistEnvironmentVariableCache) {
                        this.environmentCacheUtil.updateEnvironmentCache(env.getId(),
                            environmentVariableFromDb.getWorkspaceId(), environmentVariableFromDb.getEnvVariable());
                    }
                });
                return environmentVariableResp;
            }).toList();
        }
        EnvironmentVariablesResp resp = new EnvironmentVariablesResp();
        resp.setVariables(environmentVariablesList);
        resp.setTotal(environmentManagerEntities.size());
        return resp;
    }

    /**
     * 查询当前环境和空间下的环境变量
     *
     * @param projectId 项目id
     * @param environmentId 环境id
     * @param workspaceId 空间id
     */
    public String queryEnvironmentVariables(String projectId, String environmentId, String workspaceId) {
        EnvironmentManagerEntity envInfo = environmentManagerMapper.findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            return "";
        }
        String variableInfo = this.environmentCacheUtil.getEnvironmentCache(envInfo.getId(), workspaceId);
        if (StringUtils.isNotBlank(variableInfo)) {
            return variableInfo;
        }
        EnvironmentVariableEntity environmentVariable = environmentVariableMapper
            .findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId, environmentId);
        return environmentVariable == null ? "" : environmentVariable.getEnvVariable();
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Environment",
        description = "创建环境变量",
        resourceId = "environmentId",
        resourceName = ""
    )
    public String createEnvironmentVariables(String projectId, String environmentId, String workspaceId,
        EnvironmentVariables body) {
        if (body == null) {
            throw new AgentStudioException(ENVIRONMENT_VARIABLE_NOT_EMPTY);
        }
        if (body.getVariables() != null && body.getVariables().size() > environmentVariablesQuota) {
            log.error("The number of environment variables in a single environment has exceeded the maximum limit supported by the system {}", environmentVariablesQuota);
            throw new AgentStudioException(ENVIRONMENT_VARIABLES_LIMIT_EXCEEDED, environmentVariablesQuota);
        }
        EnvironmentManagerEntity environmentManagerEntity = this.queryEnvironmentDetail(projectId, environmentId);
        EnvironmentVariableEntity environmentVariableEntity
            = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId,
            environmentId);
        Map<String, EnvironmentVariableValue> secretVariables = new HashMap<>();
        String variables;
        if (environmentVariableEntity != null && StringUtils.isNotBlank(environmentVariableEntity.getEnvVariable())) {
            List<EnvironmentVariable> environmentVariables = JsonUtils.json2Array(environmentVariableEntity.getEnvVariable(), EnvironmentVariable.class);
            if (!CollectionUtils.isEmpty(environmentVariables)) {
                secretVariables = environmentVariables.stream()
                    .filter(variable -> variable.getValue().isSecret())
                    .collect(Collectors.toMap(EnvironmentVariable::getName,
                        EnvironmentVariable::getValue,
                        (oldValue, newValue) -> newValue));
            }
            variables = this.parseEnvVariable(body.getVariables(), secretVariables);
            boolean isUpdateSuccess = this.updateEvnVariable(environmentId,
                variables, workspaceId, environmentVariableEntity.getId());
            return isUpdateSuccess ? SUCCESS : FAIL;
        }
        variables = this.parseEnvVariable(body.getVariables(), secretVariables);
        boolean isInsertSuccess = this.insertEvnVariable(environmentId, variables, workspaceId);
        return isInsertSuccess ? SUCCESS : FAIL;
    }

    private boolean updateEvnVariable(String environmentId, String variables, String workspaceId, String variableId) {
        int count = environmentVariableMapper.updateEvnVariableById(variableId, variables, CommonUtil.getUserId());
        if (count > 0) {
            environmentCacheUtil.updateEnvironmentCache(environmentId, workspaceId, variables);
        }
        return count > 0;
    }

    private boolean insertEvnVariable(String environmentId, String variables, String workspaceId) {
        EnvironmentVariableEntity entity = new EnvironmentVariableEntity();
        entity.setCreatorId(RequestContextUtils.getRequestUserId());
        entity.setProjectId(RequestContextUtils.getRequestProjectId());
        entity.setUpdaterId(RequestContextUtils.getRequestUserId());
        entity.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
        entity.setCreatedOn(new Date());
        entity.setUpdatedOn(new Date());
        entity.setEnvId(environmentId);
        entity.setEnvVariable(variables);
        try {
            environmentVariableMapper.insert(entity);
            environmentCacheUtil.updateEnvironmentCache(environmentId, workspaceId,
                entity.getEnvVariable());
            return true;
        } catch (Exception e) {
            throw new AgentStudioException(ENVIRONMENT_VARIABLE_CREATE_FAIL);
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Environment",
        description = "删除环境变量",
        resourceId = "environmentId",
        resourceName = ""
    )
    public String deleteEnvironmentVariables(String projectId, String environmentId,
        String envVariableId, String workspaceId) {
        EnvironmentManagerEntity envInfo = this.queryEnvironmentDetail(projectId, environmentId);
        EnvironmentVariableEntity environmentVariableEntity
            = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvIdAndId(projectId, workspaceId,
            environmentId, envVariableId);
        if (environmentVariableEntity == null) {
            throw new AgentStudioException(ENVIRONMENT_VARIABLE_NOT_EXISTS);
        }
        try {
            environmentVariableMapper.deleteById(environmentVariableEntity.getId());
            environmentCacheUtil.deleteEnvironmentCache(envInfo.getId(), workspaceId);
            return SUCCESS;
        } catch (Exception e) {
            throw new AgentStudioException(ENVIRONMENT_VARIABLE_DELETE_FAIL);
        }
    }

    private void deleteAllEnvironmentVariables(String projectId, String environmentId) {
        EnvironmentManagerEntity envInfo = this.queryEnvironmentDetail(projectId, environmentId);
        List<EnvironmentVariableEntity> environmentVariables
            = environmentVariableMapper.findByProjectIdAndEnvId(projectId, environmentId);
        if (CollectionUtils.isEmpty(environmentVariables)) {
            return;
        }
        try {
            environmentVariables.forEach(envVariable -> {
                environmentVariableMapper.deleteById(envVariable.getId());
                environmentCacheUtil.deleteEnvironmentCache(envInfo.getId(), envVariable.getWorkspaceId());
            });
        } catch (Exception e) {
            // 缓存数据回滚
            environmentVariables.forEach(
                envVariableEntity -> environmentCacheUtil.updateEnvironmentCache(envInfo.getId(),
                    envVariableEntity.getWorkspaceId(), envVariableEntity.getEnvVariable()));
            throw new AgentStudioException(ENVIRONMENT_VARIABLE_DELETE_FAIL);
        }
    }

    private CreateEnvOpsMetaData buildCaeMetaData(Vpc vpcInfo, Subnet subnetInfo, Map<String, Object> envInfo) {
        return CreateEnvOpsMetaData.builder()
            .environmentName(String.valueOf(envInfo.get(ENV_NAME)))
            .description(String.valueOf(envInfo.get("desc")))
            .vpcId(vpcInfo.getId())
            .subnetId(subnetInfo.getId())
            .build();
    }

    private Vpc checkVpc(String vpcId) {
        if (!opsCallSwitch) {
            return new Vpc();
        }
        if (StringUtils.isBlank(vpcId)) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL, "vpcId");
        }
        Optional<ShowVpcResponse> showVpcResponse = this.environmentClientService.showVpc(
            RequestContextUtils.getRequestAuthToken(), RequestContextUtils.getRequestProjectId(), vpcId);
        if (showVpcResponse.isEmpty() || showVpcResponse.get().getVpc() == null) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_WITH_VPC_NOT_EXIST);
        }
        return showVpcResponse.get().getVpc();
    }

    private Subnet checkSubnet(String subnetId) {
        if (!opsCallSwitch) {
            return new Subnet();
        }
        if (StringUtils.isBlank(subnetId)) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL, "subnetId");
        }
        Optional<ShowSubnetResponse> subnet = this.environmentClientService.showSubnet(
            RequestContextUtils.getRequestAuthToken(), RequestContextUtils.getRequestProjectId(), subnetId);
        if (subnet.isEmpty() || subnet.get().getSubnet() == null) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_WITH_SUBNET_NOT_EXIST);
        }
        return subnet.get().getSubnet();
    }

    private void checkEnvName(String name, String projectId) {
        if (StringUtils.isBlank(name)) {
            throw new AgentStudioException(ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL, ENV_NAME);
        }
        List<EnvironmentManagerEntity> envs
            = environmentManagerMapper.findByNameAndProjectId(name, projectId);
        if (!CollectionUtils.isEmpty(envs)) {
            throw new AgentStudioException(ENVIRONMENT_NAME_EXIST);
        }
    }

    private void validationQuota(String projectId) {
        int total = environmentManagerMapper.countByProjectId(projectId);
        if (total >= environmentQuota) {
            throw new AgentStudioException(ENVIRONMENT_LIMIT_EXCEEDED, environmentQuota);
        }
    }

    @Override
    public List<VpcInfo> queryVpcs(String projectId) {
        if (!opsCallSwitch) {
            return List.of(new VpcInfo());
        }
        ListVpcsResponse vpcResp = this.environmentClientService.listVpcs(RequestContextUtils.getRequestAuthToken(),
            RequestContextUtils.getRequestProjectId());
        if (vpcResp == null || CollectionUtils.isEmpty(vpcResp.getVpcs())) {
            return new ArrayList<>();
        }
        return vpcResp.getVpcs().stream().map(vpc -> {
            VpcInfo vpcInfo = new VpcInfo();
            BeanUtils.copyProperties(vpc, vpcInfo);
            return vpcInfo;
        }).toList();
    }

    @Override
    public ListSubnets queryVpcsSubnets(String projectId, String vpcId) {
        if (!opsCallSwitch) {
            return new ListSubnets();
        }
        ListSubnetsResponse listSubnetsResponse = this.environmentClientService.listSubnets(
            RequestContextUtils.getRequestAuthToken(), RequestContextUtils.getRequestProjectId(), vpcId);
        ListSubnets listSubnets = new ListSubnets();
        if (listSubnetsResponse == null || CollectionUtils.isEmpty(listSubnetsResponse.getSubnets())) {
            return listSubnets;
        }
        List<SubnetInfo> subnetInfos = listSubnetsResponse.getSubnets().stream().map(subnet -> {
            SubnetInfo subnetInfo = new SubnetInfo();
            BeanUtils.copyProperties(subnet, subnetInfo);
            subnetInfo.setStatus(subnet.getStatus().getValue());
            return subnetInfo;
        }).toList();
        listSubnets.setSubnet(subnetInfos);
        return listSubnets;
    }

    @Override
    public EnvironmentVariables showEnvironmentVariables(String projectId, String environmentId, String workspaceId) {

        EnvironmentManagerEntity envInfo = environmentManagerMapper.findByIdAndProjectId(environmentId, projectId);
        if (envInfo == null) {
            throw new AgentStudioException(ENVIRONMENT_NOT_EXIST);
        }
        String variableInfo = this.environmentCacheUtil.getEnvironmentCache(envInfo.getId(), workspaceId);
        if (StringUtils.isBlank(variableInfo)) {
            EnvironmentVariableEntity environmentVariableFromDb
                = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId,
                environmentId);
            if (environmentVariableFromDb == null) {
                return new EnvironmentVariables();
            }
            variableInfo = environmentVariableFromDb.getEnvVariable();
        }
        List<EnvironmentVariable> environmentVariables = JsonUtils.json2Array(variableInfo, EnvironmentVariable.class);
        if (!CollectionUtils.isEmpty(environmentVariables)) {
            environmentVariables.forEach(variable -> {
                if (variable.getValue() != null && variable.getValue().isSecret()) {
                    variable.getValue().setContent(PASSWORD_PLACEHOLDER);
                }
            });
        }
        EnvironmentVariables envVariables = new EnvironmentVariables();
        envVariables.setVariables(environmentVariables);
        return envVariables;
    }

    /**
     * 按环境名称条件分页查询
     *
     * @param name 查询条件 环境名称
     * @param projectId 项目id
     * @param pageable 分页信息
     */
    public Page<EnvironmentManagerEntity> selectByConditionWithPage(String name, String projectId, Pageable pageable) {
        List<EnvironmentManagerEntity> environmentManagerEntities = environmentManagerMapper.selectByConditionWithPage(name, projectId, (int) pageable.getOffset(), pageable.getPageSize());
        long total = environmentManagerMapper.countByCondition(name,projectId);
        return new PageImpl<>(environmentManagerEntities,pageable,total);
    }

    /**
     * 按环境状态条件分页查询
     *
     * @param status 查询条件 环境状态
     * @param projectId 项目id
     * @param pageable 分页信息
     */
    public Page<EnvironmentManagerEntity> selectByStatusConditionWithPage(String status, String projectId, Pageable pageable) {
        List<EnvironmentManagerEntity> environmentManagerEntities = environmentManagerMapper.selectByStatusConditionWithPage(status, projectId, (int) pageable.getOffset(), pageable.getPageSize());
        long total = environmentManagerMapper.countByStatus(status,projectId);
        return new PageImpl<>(environmentManagerEntities,pageable,total);
    }


    /**
     * 工作流发布，环境变量副本写入obs
     *
     * @param projectId 项目id
     * @param flowId 应用环境变量的工作流id
     * @param environmentId 工作流中使用的环境变量id
     * @param workspaceId 工作空间
     * @param flowVersion 工作流的版本
     */
    public boolean uploadEnvironmentVarToObsFile(String projectId, String flowId, String environmentId,
        String workspaceId, String flowVersion) {
        EnvironmentManagerEntity envInfo = this.queryEnvironmentDetail(projectId, environmentId);
        EnvironmentVariableEntity variableEntity
            = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId,
            environmentId);
        obsService.uploadObsFile(flowId, StringUtils.join(flowId, "_", flowVersion, "_env"), CommonConstant.WORKFLOW,
            variableEntity == null ? "" : variableEntity.getEnvVariable(), CommonConstant.Workflow.IR);
        return true;
    }

    public boolean uploadEnvironmentVarToObsFileForController(String projectId, String agentId, String environmentId,
        String workspaceId, String flowVersion) {
        EnvironmentManagerEntity envInfo = this.queryEnvironmentDetail(projectId, environmentId);
        EnvironmentVariableEntity variableEntity
            = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId,
            environmentId);
        obsService.uploadObsFile(agentId, StringUtils.join(agentId, "_", flowVersion, "_env"), CommonConstant.AGENT,
            variableEntity == null ? "" : variableEntity.getEnvVariable(), CommonConstant.Workflow.IR);
        return true;
    }

    /**
     * 解析环境变量
     *
     * @param variables 对象类型的环境变量
     * @param secretVariables 环境变量密文
     */
    private String parseEnvVariable(List<EnvironmentVariable> variables,
        Map<String, EnvironmentVariableValue> secretVariables) {
        List<EnvironmentVariable> envVariables = new ArrayList<>();
        variables.forEach(envVari -> {
            String content = envVari.getValue().getContent();
            if (envVari.getValue() == null || StringUtils.isBlank(envVari.getValue().getContent())) {
                content = "";
            } else if (envVari.getValue().isSecret() && Strings.CS.equals(envVari.getValue().getContent(),
                PASSWORD_PLACEHOLDER)) {
                content = CryptoUtils.encrypt(envVari.getValue().getContent());
            } else if (envVari.getValue().isSecret() && !Strings.CS.equals(envVari.getValue().getContent(),
                PASSWORD_PLACEHOLDER)) {
                content = CryptoUtils.encrypt(envVari.getValue().getContent());
            }
            EnvironmentVariable variable = buildEnvironmentVariable(envVari.getName(),
                envVari.getValue().getType() == null ? EnvironmentVariableValue.TypeEnum.STRING : envVari.getValue().getType(),
                content, envVari.getValue() != null && envVari.getValue().isSecret());
            envVariables.add(variable);
        });
        return JsonUtils.toJson(envVariables);
    }

    /**
     * 环境越权校验  对历史数据兼容，环境变量如果未空，不做校验
     *
     * @param environment 环境信息
     */
    public void validateEnvironmentId(String environment) {
        if (StringUtils.isBlank(environment)) {
            return;
        }
        if (JsonUtils.isJsonString(environment) || Strings.CS.equals("hc", envType)) {
            return;
        }
        if (ENVIRONMENT_NAME_IN_WORKFLOW_REGEX.matcher(environment).lookingAt()) {
            return;
        }
        this.queryEnvironmentDetail(RequestContextUtils.getRequestProjectId(), environment);
    }
    @Override
    public Resource exportEnvironmentVariable(String projectId, String workspaceId,
        EnvironmentVariablesExport body) {
        if (body == null || CollectionUtils.isEmpty(body.getEnvironmentId()) || body.getEnvironmentId().size() != 1) {
            throw new AgentStudioException(StudioError.EXPORT_ENVIRONMENT_VARIABLE_FAIL);
        }
        List<EnvironmentManagerEntity> environments = environmentManagerMapper.findByProjectId(projectId);
        if (CollectionUtils.isEmpty(environments)) {
            throw new AgentStudioException(StudioError.EXPORT_ENVIRONMENT_VARIABLE_FAIL);
        }
        List<String> envIds = environments.stream()
            .map(EnvironmentManagerEntity::getId)
            .toList();
        List<String> exportIdsTemp = new ArrayList<>(body.getEnvironmentId().stream().toList());
        exportIdsTemp.removeAll(envIds);
        if (!CollectionUtils.isEmpty(exportIdsTemp)) {
            throw new AgentStudioException(StudioError.EXPORT_ENVIRONMENT_VARIABLE_FAIL);
        }
        List<EnvironmentVariablesExportAndImportDetail> variablesExportDetails = new ArrayList<>();
        body.getEnvironmentId().forEach(id -> {
            String cacheVariables = this.environmentCacheUtil.getEnvironmentCache(id, workspaceId);
            if (StringUtils.isBlank(cacheVariables)) {
                EnvironmentVariableEntity variable = environmentVariableMapper
                    .findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId, id);
                cacheVariables = variable == null ? "" : variable.getEnvVariable();
            }
            List<EnvironmentVariable> environmentVariables = JsonUtils.json2Array(cacheVariables, EnvironmentVariable.class);
            if (!CollectionUtils.isEmpty(environmentVariables)) {
                environmentVariables.forEach(variable -> {
                    if (variable.getValue() != null && variable.getValue().isSecret()) {
                        variable.getValue().setContent("");
                    }
                });
            }
            variablesExportDetails.add(EnvironmentVariablesExportAndImportDetail.builder()
                .environmentId(id)
                .environmentVariables(environmentVariables).build());
        });
        EnvironmentVariablesExportAndImport exportInfo = EnvironmentVariablesExportAndImport.builder()
            .detail(variablesExportDetails)
            .importType(CommonConstant.ENVIRONMENT)
            .build();
        byte[] bytesAllVariables = JSON.toJSONString(exportInfo, JSONWriter.Feature.WriteNulls)
            .getBytes(StandardCharsets.UTF_8);
        ResponseModel.TransferResource resource =
            new ResponseModel.TransferResource(new ByteArrayInputStream(bytesAllVariables));
        resource.setFilename("environmentVariables.jsonl");
        resource.setLength((long) bytesAllVariables.length);
        return resource;
    }

    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Environment",
        description = "导入环境变量",
        resourceId = "environmentId",
        resourceName = ""
    )
    public Boolean importEnvironmentVariable(String workspaceId, String projectId, String environmentId, List<String> coverVariables, MultipartFile file) {
        FileCommonUtils.validatedFile(file, fileMaxSize * 1024, IMPORT_ENV_FILE_TYPE);
        boolean response = false;
        try (BufferedReader bufferedReader =
            new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;

            // 逐行读取导入文件中的jsonl
            while ((line = bufferedReader.readLine()) != null) {
                EnvironmentVariablesExportAndImport evnImportInfo =
                    jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                if (evnImportInfo == null
                    || CollectionUtils.isEmpty(evnImportInfo.getDetail())
                    || !Strings.CS.equals(evnImportInfo.getImportType(), CommonConstant.ENVIRONMENT)) {
                    log.error("Environment variable import failed because the file content is error");
                    throw new AgentStudioException(StudioError.IMPORT_ENVIRONMENT_VARIABLE_FAIL);
                }
                evnImportInfo.getDetail().get(0).setEnvironmentId(environmentId);
                response = importEnvironmentVariable(projectId, workspaceId, evnImportInfo.getDetail().get(0), coverVariables == null ? new ArrayList<>() : coverVariables);
            }
        } catch (AgentStudioException e) {
            log.error("Failed to import the environment variable.", e);
            throw e;
        } catch (Exception e) {
            log.error("Failed to import the environment variable.", e);
            throw new AgentStudioException(StudioError.IMPORT_ENVIRONMENT_VARIABLE_FAIL);
        }
        return response;
    }

    /**
     * 环境变量导入
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @param coverVariables 导入环境变量重名时，需要覆盖的环境变量
     * @param importDetail 导入环境变量
     */
    private boolean importEnvironmentVariable(String projectId, String workspaceId, EnvironmentVariablesExportAndImportDetail importDetail, List<String> coverVariables) {
        if (CollectionUtils.isEmpty(importDetail.getEnvironmentVariables())) {
            return false;
        }
        if (importDetail.getEnvironmentVariables().size() > environmentVariablesQuota) {
            log.error("The number of environment variables in a single environment has exceeded the maximum limit supported by the system {}", environmentVariablesQuota);
            throw new AgentStudioException(ENVIRONMENT_VARIABLES_LIMIT_EXCEEDED, environmentVariablesQuota);
        }
        EnvironmentManagerEntity environmentManager = environmentManagerMapper.findByIdAndProjectId(
            importDetail.getEnvironmentId(), projectId);
        if (environmentManager == null) {
            log.error("The environment does not exist");
            throw new AgentStudioException(StudioError.ENVIRONMENT_NOT_EXIST);
        }
        this.validationDuplicateVariableName(importDetail);
        String variableValue;
        EnvironmentVariableEntity environmentVariable
            = environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(projectId, workspaceId,
            environmentManager.getId());
        if (environmentVariable == null) {
            variableValue = this.importEnvVariableParse(importDetail.getEnvironmentVariables(), true);
            return this.insertEvnVariable(environmentManager.getId(), variableValue, workspaceId);
        }
        List<EnvironmentVariable> variables = JsonUtils.json2Array(environmentVariable.getEnvVariable(), EnvironmentVariable.class);
        if (CollectionUtils.isEmpty(variables)) {
            variableValue = this.importEnvVariableParse(importDetail.getEnvironmentVariables(), true);
            return this.updateEvnVariable(environmentManager.getId(),
                variableValue, workspaceId, environmentVariable.getId());
        }
        Map<String, EnvironmentVariable> collectVariables = variables.stream()
            .collect(Collectors.toMap(EnvironmentVariable::getName, v -> v, (newValue, oldValue) -> newValue));
        Map<String, EnvironmentVariable> collectFileImportVariables = importDetail.getEnvironmentVariables()
            .stream()
            .collect(Collectors.toMap(EnvironmentVariable::getName, var -> var, (newValue, oldValue) -> newValue));
        collectFileImportVariables.forEach((key, value) -> {
            // 敏感环境变量值置空
            if (value.getValue() != null && value.getValue().isSecret()) {
                value.getValue().setContent("");
            }
            if (coverVariables.contains(key)) {
                collectVariables.put(key, value);
            } else {
                collectVariables.putIfAbsent(key, value);
            }
        });
        if (collectVariables.size() > environmentVariablesQuota) {
            log.error("The number of environment variables in a single environment has exceeded the maximum limit supported by the system {}", environmentVariablesQuota);
            throw new AgentStudioException(ENVIRONMENT_VARIABLES_LIMIT_EXCEEDED, environmentVariablesQuota);
        }
        variableValue = this.importEnvVariableParse(new ArrayList<>(collectVariables.values()), false);
        return this.updateEvnVariable(environmentManager.getId(),
            variableValue, workspaceId, environmentVariable.getId());
    }

    /**
     * 导入环境变量解析
     *
     * @param variables 导入的环境变量列表
     * @param isEmpty 设置为空值的标识
     */
    private String importEnvVariableParse(List<EnvironmentVariable> variables, boolean isEmpty) {
        List<EnvironmentVariable> strEnvVariable = new ArrayList<>();
        variables.forEach(envVari -> {
            if (envVari.getValue() == null) {
                return;
            }
            String content = envVari.getValue().getContent();

            // 环境变量导入，如果是敏感变量，导入空值
            if (envVari.getValue().isSecret() && isEmpty) {
                content = "";
            }
            EnvironmentVariable variable = buildEnvironmentVariable(envVari.getName(),
                envVari.getValue().getType() == null ? EnvironmentVariableValue.TypeEnum.STRING : envVari.getValue().getType(),
                content, envVari.getValue() != null && envVari.getValue().isSecret());
            strEnvVariable.add(variable);
        });
        return JsonUtils.toJson(strEnvVariable);
    }

    /**
     * 构建环境变量存储结构
     *
     * @param name 环境变量名称
     * @param type 环境变量类型
     * @param content 环境变量值
     * @param secret 是否加密标识
     */
    private EnvironmentVariable buildEnvironmentVariable(String name, EnvironmentVariableValue.TypeEnum type, String content, boolean secret) {
        EnvironmentVariableValue variableValue = new EnvironmentVariableValue();
        variableValue.setType(type);
        variableValue.setContent(content);
        variableValue.setSecret(secret);
        EnvironmentVariable variable = new EnvironmentVariable();
        variable.setName(name);
        variable.setValue(variableValue);
        return variable;
    }

    /**
     * 环境变量导入文件检查和校验
     *
     * @param projectId 项目id
     * @param importDetail 导入的环境变量信息
     */
    public ValidationVariablesImport resolveEnvironmentVariables(String projectId, EnvironmentVariablesExportAndImportDetail importDetail, String environmentId) {
        ValidationVariablesImport validationVariablesImport = new ValidationVariablesImport();
        EnvironmentManagerEntity environmentManager = environmentManagerMapper.findByIdAndProjectId(
            environmentId, projectId);
        if (environmentManager == null) {
            log.error("The environment does not exist");
            throw new AgentStudioException(StudioError.ENVIRONMENT_NOT_EXIST);
        }
        if (importDetail == null || CollectionUtils.isEmpty(importDetail.getEnvironmentVariables())) {
            log.error("The environment variable is empty");
            throw new AgentStudioException(StudioError.IMPORT_ENVIRONMENT_VARIABLE_FAIL);
        }
        this.validationDuplicateVariableName(importDetail);
        EnvironmentVariableEntity environmentVariable = environmentVariableMapper
            .findByProjectIdAndWorkspaceIdAndEnvId(projectId, RequestContextUtils.getRequestWorkspaceId(), environmentManager.getId());
        if (environmentVariable == null) {
            return validationVariablesImport.setResult(true);
        }
        List<EnvironmentVariable> variables = JsonUtils.json2Array(environmentVariable.getEnvVariable(), EnvironmentVariable.class);
        if (CollectionUtils.isEmpty(variables)) {
            return validationVariablesImport.setResult(true);
        }
        Map<String, EnvironmentVariable> existsVariables = variables.stream()
            .collect(Collectors.toMap(EnvironmentVariable::getName, v -> v, (newValue, oldValue) -> newValue));
        Map<String, EnvironmentVariable> importVariables = importDetail.getEnvironmentVariables()
            .stream()
            .collect(Collectors.toMap(EnvironmentVariable::getName, var -> var, (newValue, oldValue) -> newValue));
        List<ValidationVariableImport> validationVariableImports = new ArrayList<>();
        importVariables.forEach((key, value) -> {
            if (!existsVariables.containsKey(key)) {
                return;
            }
            ValidationVariableImport validationVariableImport = new ValidationVariableImport();
            validationVariableImport.setVariableName(key);
            validationVariableImport.setVariableValue((existsVariables.get(key) == null || existsVariables.get(key).getValue() == null) ? "" : existsVariables.get(key).getValue().getContent());
            validationVariableImport.setValidateResult("exist");
            validationVariableImport.setVariableType((existsVariables.get(key) == null || existsVariables.get(key).getValue() == null)
                ? EnvironmentVariableValue.TypeEnum.STRING.toString()
                : existsVariables.get(key).getValue().getType().toString());
            validationVariableImport.setIsSecret(existsVariables.get(key) != null && existsVariables.get(key).getValue() != null
                && existsVariables.get(key).getValue().isSecret());
            validationVariableImports.add(validationVariableImport);
        });
        return validationVariablesImport.setResult(true).setVariables(validationVariableImports);
    }

    /**
     * 环境变量导入，校验变量是否重名
     *
     * @param importDetail 导入的环境变量
     */
    private void validationDuplicateVariableName(EnvironmentVariablesExportAndImportDetail importDetail) {
        long count = importDetail.getEnvironmentVariables()
            .stream()
            .map(EnvironmentVariable::getName)
            .distinct()
            .count();
        if (importDetail.getEnvironmentVariables().size() != count) {
            throw new AgentStudioException(StudioError.ENVIRONMENT_VARIABLES_DUPLICATE_NAMES);
        }
    }

    /**
     * 解析导入文件
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @return listImportFile 根据文件内容解析出来的配置
     */
    @Override
    public ValidationVariablesImport environmentVariableImportFileValidation(String workspaceId, String projectId, String environmentId, MultipartFile file) {
        FileCommonUtils.validatedFile(file, fileMaxSize * 1024, IMPORT_ENV_FILE_TYPE);
        ValidationVariablesImport validationVariablesImport = new ValidationVariablesImport();
        try (BufferedReader bufferedReader =
            new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = bufferedReader.readLine()) != null) {
                Map<String, Object> jsonMap = jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                if (!jsonMap.containsKey(CommonConstant.IMPORT_TYPE)) {
                    log.error("Incorrect file format.");
                    throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                }

                if (jsonMap.get(CommonConstant.IMPORT_TYPE).toString().equals(CommonConstant.ENVIRONMENT)) {
                    List<EnvironmentVariablesExportAndImportDetail> environmentVariablesImportDetails
                        = jacksonObjectMapper.convertValue(jsonMap.get("detail"), new TypeReference<>() {});
                    if (org.apache.commons.collections4.CollectionUtils.isEmpty(environmentVariablesImportDetails)) {
                        log.error("The environment variable is empty");
                        throw new AgentStudioException(StudioError.IMPORT_ENVIRONMENT_VARIABLE_FAIL);
                    }
                    validationVariablesImport = this.resolveEnvironmentVariables(projectId, environmentVariablesImportDetails.get(0), environmentId);
                } else {
                    log.error("import file type error");
                    throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                }
            }
        } catch (AgentStudioException e) {
            log.error("environment variable import validation failed", e);
            throw e;
        } catch (Exception e) {
            log.error("import environment variables file error", e);
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return validationVariablesImport;
    }
}

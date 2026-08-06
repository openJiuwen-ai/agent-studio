/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.EN_LANGUAGE;

import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.md.ProviderAuth;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderRsp;
import com.openjiuwen.studio.agent.manager.dto.ProviderAuthConfig;
import com.openjiuwen.studio.agent.manager.dto.ProviderAuthInfoReq;
import com.openjiuwen.studio.agent.manager.dto.QueryPlatformProvidersQo;
import com.openjiuwen.studio.agent.manager.dto.QueryUserProvidersQo;
import com.openjiuwen.studio.agent.manager.entity.ProviderExportMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderCondition;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.SysModelServiceProviderMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.UserModelServiceProviderMapper;
import com.openjiuwen.studio.agent.manager.service.IProviderMgmtService;
import com.openjiuwen.studio.prompt.engineering.utils.HttpUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 供应商管理
 */
@Slf4j
@Service
public class ProviderMgmtService implements IProviderMgmtService {
    @Autowired
    private SysModelServiceProviderMapper sysProviderMapper;

    @Autowired
    private UserModelServiceProviderMapper userProviderMapper;

    @Autowired
    private UserModelServiceProviderMapper userModelServiceProviderMapper;

    @Autowired
    private ProviderAuthMetadataMapper metadataMapper;

    @Autowired
    private ProviderAuthDataMapper authMapper;

    @Autowired
    private ProviderAuthService authService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ModelLicenseCtrlService licenseCtrlService;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Value("${model.soft.delete.enable:false}")
    private boolean modelSoftDelete;

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "ModelServiceProvider",
        description = "创建模型服务供应商",
        resourceId = "-1",
        resourceName = "body.providerName"
    )
    public String createModelServiceProviders(String projectId, String workspaceId, ModelServiceProviderReq body) {
        licenseCtrlService.canAccessIntegrationModel();

        List<ModelServiceProvider> providers = userProviderMapper.selectUserDataByName(projectId, workspaceId,
            body.getProviderName());
        if (!providers.isEmpty()) {
            log.error("Provider name is already exist. name:{} project:{} workspace:{}", body.getProviderName(),
                projectId, workspaceId);
            throw new AgentStudioException(StudioError.PROVIDER_NAME_REPEATED);
        }
        String id = UUID.randomUUID().toString();
        String user = RequestContextUtils.getRequestUserName();
        String domainId = RequestContextUtils.getRequestUserDomainId();
        long time = System.currentTimeMillis();

        ProviderAuth authCfg = authService.getProviderAuth(body.getAuthType(), body.getAuthInfo());
        authCfg.validCheck();

        if (null != body.getProviderUrl() && !body.getProviderUrl().isEmpty()) {
            urlCheckUtils.checkUrlInWhiteList(body.getProviderUrl());
        }

        ModelServiceProvider provider = new ModelServiceProvider().setId(id)
            .setProviderName(body.getProviderName())
            .setProviderNameEn(body.getProviderNameEn())
            .setDescription(body.getDescription())
            .setTags(body.getTags())
            .setProviderUrl(body.getProviderUrl())
            .setLogo(body.getLogo())
            .setStatus("created")
            .setDomainId(domainId)
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setCreatedByUser(user)
            .setLastUpdatedByUser(user)
            .setCreatedDate(time)
            .setLastUpdatedDate(time)
            .setIdentityId(id);

        userModelServiceProviderMapper.insert(provider);

        String metaId = UUID.randomUUID().toString();
        try {
            ProviderAuthMetadata metadata = new ProviderAuthMetadata().setId(metaId)
                .setProviderId(id)
                .setAuthType(body.getAuthType())
                .setAuthInfo(authCfg.authInfoTemplate())
                .setAuthUrl("")
                .setCreatedByUser(user)
                .setDomainId(domainId)
                .setProjectId(projectId)
                .setWorkspaceId(workspaceId)
                .setCreatedDate(time)
                .setLastUpdatedDate(time)
                .setIdentityId(metaId);
            metadataMapper.insert(metadata);
        } catch (Exception e) {
            userModelServiceProviderMapper.deleteById(id);
            if (e instanceof AgentStudioException) {
                throw (AgentStudioException) e;
            }
            log.error("Insert provider auth metadata exception.", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }

        String authId = UUID.randomUUID().toString();
        try {
            ProviderAuthData config = new ProviderAuthData().setId(authId)
                .setProviderId(id)
                .setAuthMetadataId(metaId)
                .setAuthType(body.getAuthType())
                .setAuthInfo(authCfg.convertToEncryptStr())
                .setCreatedByUser(user)
                .setDomainId(domainId)
                .setProjectId(projectId)
                .setWorkspaceId(workspaceId)
                .setCreatedDate(time)
                .setLastUpdatedDate(time)
                .setIdentityId(authId);

            authService.createAuthInfo(config);
        } catch (Exception e) {
            userModelServiceProviderMapper.deleteById(id);
            metadataMapper.deleteById(metaId);
            authMapper.deleteById(authId);
            if (e instanceof AgentStudioException) {
                throw (AgentStudioException) e;
            }
            log.error("Insert auth config exception.", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }

        return id;
    }

    ModelServiceProvider queryAndAuthCheck(String projectId, String workspaceId, String id, boolean readOnly) {
        ModelServiceProvider provider = userModelServiceProviderMapper.selectById(id);
        if (provider == null || !projectId.equals(provider.getProjectId())) {
            log.error("provider not exist or not belong to project. id:{} project:{} dataProjectId:{} ", id, projectId,
                provider == null ? null : provider.getProjectId());
            throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST);
        }
        if (workspaceId.equals(provider.getWorkspaceId())) {
            return provider;
        }
        if (readOnly && "SYSTEM".equals(provider.getWorkspaceId())) {
            return provider;
        }
        log.error("provider not belong to workspace. id:{} project:{} dataWorkspace:{} readOnly:{}", id, projectId,
            provider.getWorkspaceId(), readOnly);
        throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST);
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ModelServiceProvider",
        description = "删除模型服务供应商",
        resourceId = "id",
        resourceName = ""
    )
    public Void deleteModelServiceProvider(String projectId, String workspaceId, String id) {
        queryAndAuthCheck(projectId, workspaceId, id, false);
        int count = modelServiceMapper.countByProviderId(id);
        if (count > 0) {
            throw new AgentStudioException(StudioError.PROVIDER_ASSOCIATED_MODEL);
        }
        // 数据删除备份
        if (modelSoftDelete) {
            ModelServiceProvider modelServiceProvider = userModelServiceProviderMapper.selectById(id);
            modelServiceProvider.setLastUpdatedDate(System.currentTimeMillis());
            userModelServiceProviderMapper.insertBackup(modelServiceProvider);
            authService.backupByProvider(projectId, workspaceId, id);
            List<ProviderAuthMetadata> providerAuthMetadataList = metadataMapper.selectByProjectWorkspaceProvider(
                projectId, workspaceId, id);
            for (ProviderAuthMetadata providerAuthMetadata : providerAuthMetadataList) {
                providerAuthMetadata.setLastUpdatedDate(System.currentTimeMillis());
                metadataMapper.insertBackup(providerAuthMetadata);
            }
        }
        userModelServiceProviderMapper.deleteById(id);
        authService.deleteByProvider(projectId, workspaceId, id);
        metadataMapper.deleteByProviderId(projectId, workspaceId, id);
        return null;
    }

    @Override
    public ModelServiceProviderRsp integrationModelServiceProviderDetail(String projectId, String workspaceId,
        String id) {
        ModelServiceProvider provider = sysProviderMapper.selectById(id);
        if (provider != null) {
            return getModelServiceProviderRsp(projectId, workspaceId, id, provider, true);
        }
        provider = queryAndAuthCheck(projectId, workspaceId, id, true);

        return getModelServiceProviderRsp(projectId, workspaceId, id, provider, false);
    }

    private @NotNull ModelServiceProviderRsp getModelServiceProviderRsp(String projectId, String workspaceId, String id,
        ModelServiceProvider provider, boolean isPlatformProvider) {
        ModelServiceProviderRsp rsp = transToModelServiceProviderRsp(provider, isPlatformProvider);

        List<ProviderAuthMetadata> authConfigs = authMapper.selectProviderAuthData(projectId, workspaceId, id);

        List<ProviderAuthConfig> configs = new ArrayList<>(authConfigs.size());
        int existAuthNum = 0;
        for (ProviderAuthMetadata auth : authConfigs) {
            configs.add(authService.transToAuthConfig(auth));
            if (auth.getAuthId() != null && auth.getAuthConfig() != null) {
                existAuthNum++;
                break;
            }
        }
        rsp.setAuthConfigs(configs);
        if (existAuthNum == 0) {
            rsp.setAuthConfigStatus("no_exist");
        } else {
            rsp.setAuthConfigStatus("available");
        }

        return rsp;
    }

    private ModelServiceProviderRsp transToModelServiceProviderRsp(ModelServiceProvider provider,
        boolean isPlatformProvider) {
        ModelServiceProviderRsp rsp = new ModelServiceProviderRsp().setId(provider.getId())
            .setProviderNameEn(provider.getProviderNameEn())
            .setProviderName(provider.getProviderName())
            .setProviderUrl(provider.getProviderUrl())
            .setDescription(provider.getDescription())
            .setCreatedDate(provider.getCreatedDate())
            .setLastUpdatedDate(provider.getLastUpdatedDate())
            .setCreatedByUser(provider.getCreatedByUser())
            .setLastUpdatedByUser(provider.getLastUpdatedByUser())
            .setLogo(provider.getLogo())
            .setTags(provider.getTags());
        if (!isPlatformProvider) {
            rsp.setDomainId(provider.getDomainId())
                .setProjectId(provider.getProjectId())
                .setWorkspaceId(provider.getWorkspaceId());
        }
        return rsp;
    }

    @Override
    public ModelServiceProviderRsp platformModelServiceProviderDetail(String projectId, String id, String workspaceId) {
        ModelServiceProvider provider = sysProviderMapper.selectById(id);
        if (provider == null) {
            log.error("Provider is is invalid. system provider is not exit.");
            throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST);
        }
        if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
            provider.setDescription(
                provider.getDescriptionEn() == null ? provider.getDescription() : provider.getDescriptionEn());
        }
        return getModelServiceProviderRsp(projectId, workspaceId, id, provider, true);
    }

    @Override
    public ModelServiceProviderListRsp queryPlatformProviders(String projectId, QueryPlatformProvidersQo params) {
        if ("part_available".equals(params.getAuthConfigStatus())) {
            return new ModelServiceProviderListRsp().setTotal(0)
                .setData(Collections.emptyList()); // 暂时不支持一个供应商多个鉴权配置定义。所以没有部分可用的状态
        }
        String workspaceId = params.getWorkspaceId();
        ProviderCondition condition = new ProviderCondition();
        BeanUtils.copyProperties(params, condition);

        condition.setProjectId(projectId).setWorkspaceId(workspaceId);
        if (!StringUtils.isEmpty(platformProviderId)) {
            condition.setProviderIds(Collections.singletonList(platformProviderId));
        }

        condition.sqlEscapeChar();
        int offset = (params.getPageNum() - 1) * params.getPageSize();
        List<ModelServiceProviderDetail> providers = sysProviderMapper.queryByCondition(condition, params.getPageSize(),
            offset);
        return getModelServiceProviderListRsp(projectId, workspaceId, providers, null, condition, params.getPageSize(),
            offset, true);
    }

    private List<ModelServiceProviderDetail> filterModelServiceProviders(String projectId, String workspaceId,
        List<ModelServiceProviderDetail> providers, ProviderCondition condition) {
        if (providers.isEmpty()) {
            return new ArrayList<>();
        }
        Set<String> providerIds = providers.stream().map(ModelServiceProviderDetail::getId).collect(Collectors.toSet());
        List<ProviderAuthData> authDatas = authMapper.selectByProviders(projectId, workspaceId, providerIds);
        Map<String, ProviderAuthData> providerAuthMap = new HashMap<>(authDatas.size());
        for (ProviderAuthData authData : authDatas) {
            providerAuthMap.put(authData.getProviderId(), authData);
        }

        Iterator<ModelServiceProviderDetail> it = providers.iterator();
        providerIds.clear();
        while (it.hasNext()) {
            ModelServiceProviderDetail provider = it.next();
            if (providerIds.contains(provider.getId())) {
                // 重复数据，清除
                it.remove();
                continue;
            }
            providerIds.add(provider.getId());
            ProviderAuthData authData = providerAuthMap.get(provider.getId());

            if ("available".equals(condition.getAuthConfigStatus()) && (authData == null
                || authData.getAuthInfo() == null)) {
                it.remove();
                continue;
            }
            if ("no_exist".equals(condition.getAuthConfigStatus()) && (authData != null
                && authData.getAuthInfo() != null)) {
                it.remove();
                continue;
            }

            provider.setAuthMetadataNum(1);
            if (authData != null) {
                provider.setAuthIds(authData.getId()).setAuthConfigNum(1);
                if (authData.getAuthInfo() != null) {
                    provider.setAuthExistNum(1);
                }
            }
        }

        return providers;
    }

    private ModelServiceProviderListRsp getModelServiceProviderListRsp(String projectId, String workspaceId,
        List<ModelServiceProviderDetail> providers, List<ModelServiceProviderDetail> platformProviders,
        ProviderCondition condition, int pageSize, int offset, boolean isPlatform) {
        List<ModelServiceProviderDetail> allProviders = filterModelServiceProviders(projectId, workspaceId, providers,
            condition);
        if (platformProviders != null) {
            condition.setAuthConfigStatus("available");
            allProviders.addAll(filterModelServiceProviders(projectId, workspaceId, platformProviders, condition));
        }

        int total = allProviders.size();

        List<ModelServiceProviderDetail> pagedProviders = allProviders.stream().skip(offset).limit(pageSize).toList();
        List<ModelServiceProviderRsp> data = new ArrayList<>(pagedProviders.size());
        pagedProviders.forEach(pd -> data.add(getModelServiceProviderRsp(pd, isPlatform)));
        return new ModelServiceProviderListRsp().setTotal(total).setData(data);
    }

    private @NotNull ModelServiceProviderRsp getModelServiceProviderRsp(ModelServiceProviderDetail provider,
        boolean isPlatform) {
        ModelServiceProviderRsp rsp = transToModelServiceProviderRsp(provider, isPlatform);
        String[] metadataIds = StringUtils.isEmpty(provider.getAuthMetaIds())
            ? new String[0]
            : provider.getAuthMetaIds().split(",");
        String[] authTypes = StringUtils.isEmpty(provider.getAuthTypes())
            ? new String[] {"NO_AUTH"}
            : provider.getAuthTypes().split(",");

        List<ProviderAuthConfig> configs = new ArrayList<>(metadataIds.length);
        for (int idx = 0; idx < metadataIds.length; ++idx) {
            ProviderAuthConfig cfg = new ProviderAuthConfig().setMetadataId(metadataIds[idx])
                .setAuthType(authTypes[idx < authTypes.length ? idx : authTypes.length - 1]);
            configs.add(cfg);
        }

        if (provider.getAuthConfigNum() == 0 || provider.getAuthExistNum() < provider.getAuthConfigNum()) {
            rsp.setAuthConfigStatus("no_exist");
        } else if (provider.getAuthConfigNum() < configs.size()) {
            rsp.setAuthConfigStatus("part_available");
        } else {
            rsp.setAuthConfigStatus("available");
        }
        rsp.setAuthConfigs(configs);

        return rsp;
    }

    @Override
    public ModelServiceProviderListRsp queryUserProviders(String projectId, QueryUserProvidersQo params) {
        String workspaceId = params.getWorkspaceId();
        if ("part_available".equals(params.getAuthConfigStatus())) {
            return new ModelServiceProviderListRsp().setData(Collections.emptyList()).setTotal(0);
        }

        ProviderCondition condition = new ProviderCondition();
        BeanUtils.copyProperties(params, condition);
        condition.setProjectId(projectId).setWorkspaceId(workspaceId);
        condition.sqlEscapeChar();

        if (params.isFunctioncall() != null || !StringUtils.isAllEmpty(params.getModelName(), params.getModelType())) {
            ModelServiceCondition md = new ModelServiceCondition().setModelName(params.getModelName())
                .setFunctioncall(params.isFunctioncall())
                .setModelType(params.getModelType())
                .setWorkspaceId(workspaceId)
                .setProjectId(projectId);
            md.sqlEscapeChar();
            List<String> ids = modelServiceMapper.filterProviderIdsByCondition(md);
            if (ids.isEmpty()) {
                return new ModelServiceProviderListRsp().setTotal(0).setData(Collections.emptyList());
            }
            condition.setProviderIds(ids);
        }

        int offset = (params.getPageNum() - 1) * params.getPageSize();
        List<ModelServiceProviderDetail> providers = userProviderMapper.queryByCondition(condition,
            params.getPageSize(), offset);

        condition.setExcludeId(platformProviderId);
        List<ModelServiceProviderDetail> platformProviders = sysProviderMapper.queryByCondition(condition,
            params.getPageSize(), offset);

        return getModelServiceProviderListRsp(projectId, workspaceId, providers, platformProviders, condition,
            params.getPageSize(), offset, false);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelServiceProvider",
        description = "更新模型服务供应商",
        resourceId = "id",
        resourceName = "body.providerName"
    )
    public Void updateModelServiceProvider(String projectId, String workspaceId, String id, Boolean availableCheck,
        ModelServiceProviderReq body) {
        ModelServiceProvider provider = queryAndAuthCheck(projectId, workspaceId, id, false);

        ProviderAuth authCfg = null;
        List<ProviderAuthMetadata> authMetadataList = null;
        if (!StringUtils.isEmpty(body.getAuthInfo())) {
            authCfg = authService.getProviderAuth(body.getAuthType(), body.getAuthInfo());
            authCfg.validCheck();

            authMetadataList = authMapper.selectProviderAuthData(projectId, workspaceId, provider.getId());
            if (authMetadataList.isEmpty()) {
                log.error("Fail get provider auth metadata. project:{} provider:{}", provider, id);
                throw new AgentStudioException(StudioError.FAIL_GET_PROVIDE_AUTH_METADATA, provider, id);
            }
        }

        if (!provider.getProviderName().equals(body.getProviderName())) {
            // 需要校验是否重名
            List<ModelServiceProvider> existProviders = userProviderMapper.selectUserDataByName(projectId, workspaceId,
                body.getProviderName());
            if (!existProviders.isEmpty()) {
                log.error("updated Provider name is already exist. name:{} project:{}", body.getProviderName(),
                    projectId);
                throw new AgentStudioException(StudioError.PROVIDER_NAME_REPEATED);
            }
        }

        provider.setLastUpdatedDate(System.currentTimeMillis())
            .setProviderName(body.getProviderName())
            .setProviderNameEn(body.getProviderNameEn())
            .setDescription(body.getDescription())
            .setLogo(body.getLogo())
            .setLastUpdatedByUser(RequestContextUtils.getRequestUserName())
            .setTags(body.getTags())
            .setProviderUrl(body.getProviderUrl());

        userProviderMapper.updateById(provider);

        if (ObjectUtils.isEmpty(authCfg) || ObjectUtils.isEmpty(authMetadataList)) {
            log.info("Not need update provider auth info.");
            return null;
        }

        if (Boolean.TRUE.equals(availableCheck)) {
            log.info("Not need update provider auth info. provider:{}", provider.getProviderName());
        }

        if (!body.getAuthType().equals(authMetadataList.get(0).getAuthType())) {
            metadataMapper.updateMetadata(authMetadataList.get(0).getId(), body.getAuthType(),
                authCfg.authInfoTemplate(), System.currentTimeMillis());
        }
        String authId = authMetadataList.get(0).getAuthId();
        if (StringUtils.isEmpty(authId)) {
            authId = UUID.randomUUID().toString();
            ProviderAuthData config = new ProviderAuthData().setId(authId)
                .setProviderId(id)
                .setAuthMetadataId(authMetadataList.get(0).getId())
                .setAuthType(body.getAuthType())
                .setAuthInfo(authCfg.convertToEncryptStr())
                .setCreatedByUser(RequestContextUtils.getRequestUserName())
                .setDomainId(RequestContextUtils.getRequestUserDomainId())
                .setProjectId(projectId)
                .setWorkspaceId(workspaceId)
                .setCreatedDate(System.currentTimeMillis())
                .setLastUpdatedDate(System.currentTimeMillis())
                .setIdentityId(authId);

            authService.createAuthInfo(config);
        } else {
            ProviderAuthData config = authMapper.selectById(authId);
            config.setAuthType(body.getAuthType());
            config.setAuthInfo(authCfg.convertToEncryptStr());

            authService.updateAuthInfo(config);
        }

        return null;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelServiceProvider",
        description = "更新模型服务供应商鉴权信息",
        resourceId = "id",
        resourceName = ""
    )
    public Void updateModelServiceProviderAuthInfo(String projectId, String workspaceId, String id,
        Boolean availableCheck, ProviderAuthInfoReq body) {
        ProviderAuthData providerAuthData = queryAuthInfoAndCheck(projectId, workspaceId, id);
        ProviderAuth authCfg = null;
        if (!StringUtils.isEmpty(body.getAuthInfo())) {
            authCfg = authService.getProviderAuth(body.getAuthType(), body.getAuthInfo());
            authCfg.validCheck();
        }
        if (authCfg == null) {
            log.info("Not need update provider auth info.");
            return null;
        }
        if (Boolean.TRUE.equals(availableCheck)) {
            log.info("Not need update provider auth info. provider_auth_id {}", providerAuthData.getId());
        }
        providerAuthData.setAuthInfo(authCfg.convertToEncryptStr()).setAuthType(body.getAuthType());
        metadataMapper.updateMetadata(providerAuthData.getAuthMetadataId(), body.getAuthType(),
            authCfg.authInfoTemplate(), System.currentTimeMillis());
        authService.updateAuthInfo(providerAuthData);
        return null;
    }

    ProviderAuthData queryAuthInfoAndCheck(String projectId, String workspaceId, String id) {
        ProviderAuthData providerAuthData = authMapper.queryByProviderId(projectId, workspaceId, id);
        if (providerAuthData == null) {
            log.error("provider auth data not exist. id:{}", id);
            throw new AgentStudioException(StudioError.MD_AUTH_INFO_INVALID);
        }
        if (workspaceId.equals(providerAuthData.getWorkspaceId())) {
            return providerAuthData;
        }
        if ("SYSTEM".equals(providerAuthData.getWorkspaceId())) {
            return providerAuthData;
        }
        return null;
    }

    public void createProviderFromMetadata(String projectId, String workspaceId,
        ProviderExportMetadata providerExportMetadata) {
        // 1. 基础校验：访问权限与模型信息是否存在
        licenseCtrlService.canAccessIntegrationModel();
        if (providerExportMetadata == null || providerExportMetadata.getModelServiceProviderMetadata() == null
            || providerExportMetadata.getProviderAuthMetadata() == null) {
            throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST);
        }

        ModelServiceProvider modelServiceProvider = providerExportMetadata.getModelServiceProviderMetadata();
        ProviderAuthMetadata providerAuthMetadata = providerExportMetadata.getProviderAuthMetadata();
        ProviderAuthData providerAuthData = providerExportMetadata.getProviderAuthData();

        // 2. 唯一性校验：判断供应商名称是否已存在
        List<ModelServiceProvider> providers = userProviderMapper.selectUserDataByName(projectId, workspaceId,
            modelServiceProvider.getProviderName());
        if (!providers.isEmpty()) {
            log.error("Provider name already exists: {} in project: {}", modelServiceProvider.getProviderName(),
                projectId);
            throw new AgentStudioException(StudioError.PROVIDER_NAME_REPEATED);
        }

        ProviderAuth authCfg = authService.getProviderAuth(providerAuthMetadata.getAuthType(),
            providerAuthMetadata.getAuthInfo());
        authCfg.validCheck();
        if (StringUtils.isNotBlank(modelServiceProvider.getProviderUrl())) {
            urlCheckUtils.checkUrlInWhiteList(modelServiceProvider.getProviderUrl());
        }
        userModelServiceProviderMapper.insert(modelServiceProvider);
        try {
            metadataMapper.insert(providerAuthMetadata);
        } catch (Exception e) {
            userModelServiceProviderMapper.deleteById(modelServiceProvider.getId());
            log.error("Insert provider auth metadata exception.", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);

        }
        try {
            authService.createAuthInfo(providerAuthData);
        } catch (Exception e) {
            userModelServiceProviderMapper.deleteById(modelServiceProvider.getId());
            metadataMapper.deleteById(providerAuthMetadata.getId());
            authMapper.deleteById(providerAuthData.getId());
            log.error("Insert auth config exception.", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }

}

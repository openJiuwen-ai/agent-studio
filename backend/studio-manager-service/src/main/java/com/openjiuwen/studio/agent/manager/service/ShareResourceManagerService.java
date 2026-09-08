/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.ALL;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MCP_TYPE;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.PLUGIN_TYPE;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.PROMPT;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.SYS;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.TypeReference;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UuidUtils;
import com.openjiuwen.studio.agent.manager.bo.WfImportDataWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AuthWorkspaceInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.QueryShareResourceInfoByResourceIdQo;
import com.openjiuwen.studio.agent.manager.dto.QueryShareResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.QuerySharedResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionInfo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceInfo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceResp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareInfo;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;
import com.openjiuwen.studio.prompt.engineering.entity.PePromptTemplate;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;


/**
 * 跨空间资源共享管理
 *
 */
@Service
@Slf4j
public class ShareResourceManagerService implements IShareResourceManagerService {

    public static final String SHARE_WITH_ALL_WORKSPACE = "all";

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    MgObsService obsService;

    @Autowired
    private IPluginBase pluginBase;

    @Autowired
    private IPlugin pluginAdapter;

    @Resource
    private McpServiceDao mcpServiceDao;

    @Resource
    private PePromptTemplateMapper pePromptTemplateMapper;

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "ShareResource",
        description = "创建或更新共享资源",
        resourceId = "workspaceId",
        resourceName = "body.resourceName"
    )
    public Boolean createOrUpdateShareResource(String projectId, String workspaceId, ShareResourceRequestInfo body) {
        // 资源版本信息
        List<ResourceVersionInfo> versionInfos = new ArrayList<>();

        // 校验资源存在性、版本存在性和授权空间存在性
        String traceId = validResourceParam(projectId, workspaceId, body, versionInfos);

        versionInfos.sort(Comparator.comparing(ResourceVersionInfo::getVersionName));

        // 保存或更新资源共享记录  traceId待添加
        ShareResourceEntity shareResourceEntityNew = new ShareResourceEntity().setResourceId(body.getResourceId())
            .setResourceName(body.getResourceName())
            .setResourceType(body.getResourceType().toString())
            .setWorkspaceId(workspaceId)
            .setWorkspaceName(RequestContextUtils.getRequestWorkspaceName())
            .setTraceId(traceId)
            .setVersionList(JSONObject.toJSONString(versionInfos))
            .setProjectId(projectId)
            .setTenantId(RequestContextUtils.getRequestUserDomainId())
            .setCreatorId(RequestContextUtils.getRequestUserId())
            .setCreator(RequestContextUtils.getRequestUserName())
            .setCreateTime(new Date())
            .setUpdaterId(RequestContextUtils.getRequestUserId())
            .setUpdater(RequestContextUtils.getRequestUserName())
            .setUpdateTime(new Date());
        ShareResourceEntity shareResourceOld = shareResourceMapper.selectShareResourceEntityById(projectId, workspaceId,
            body.getResourceId());

        if (ObjectUtils.isEmpty(shareResourceOld)) {
            shareResourceMapper.insert(shareResourceEntityNew);
            updateResourceShareStatus(body.getResourceId(), body.getResourceType().toString(), 1);
        } else {
            shareResourceMapper.updateShareResourceEntity(shareResourceEntityNew);
        }

        mappingMapper.updateShareRelationValidStatusByShareResourceId(body.getResourceId(), true);

        createOrUpdateShareResourceScope(body.getResourceId(), body.getResourceType().toString(),
            body.getAuthWorkspaceIdList());

        return true;
    }


    @Override
    public ShareResourceResp queryShareResourceInfoByResourceId(String projectId, String resourceId,
        QueryShareResourceInfoByResourceIdQo queryShareResourceInfoByResourceIdQo) {
        ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);

        if (ObjectUtils.isEmpty(shareResourceEntity)) {
            return new ShareResourceResp();
        }

        validateWorkspaceShareByResourceOrNot(shareResourceEntity);

        ShareResourceResp shareResourceResp = new ShareResourceResp();
        shareResourceResp.setResourceId(shareResourceEntity.getResourceId());
        shareResourceResp.setResourceName(shareResourceEntity.getResourceName());
        shareResourceResp.setResourceType(shareResourceEntity.getResourceType());
        shareResourceResp.setResourceWorkspaceId(shareResourceEntity.getWorkspaceId());

        List<ShareScopeEntity> shareScopeEntities = shareScopeMapper.selectShareScopesByResourceId(resourceId);
        List<String> authWorkspaceIdList = new ArrayList<>(
            shareScopeEntities.stream().map(ShareScopeEntity::getWorkspaceId).toList());
        authWorkspaceIdList.add(shareResourceEntity.getWorkspaceId());

        List<WorkspaceEntity> workspaceEntityList = workspaceMapper.selectWorkspaceByWorkspaceIdList(
            authWorkspaceIdList);

        List<AuthWorkspaceInfo> authWorkspaceInfoList = workspaceEntityList.stream()
            .peek(workspaceEntity -> {
                if (RequestContextUtils.getRequestWorkspaceId().equals(workspaceEntity.getId())) {
                    shareResourceResp.setResourceWorkspaceName(workspaceEntity.getName());
                }
            })
            .filter(workspaceEntity -> !RequestContextUtils.getRequestWorkspaceId().equals(workspaceEntity.getId()))
            .map(workspaceEntity -> {
                AuthWorkspaceInfo authWorkspaceInfo = new AuthWorkspaceInfo();
                authWorkspaceInfo.setWorkspaceId(workspaceEntity.getId());
                authWorkspaceInfo.setWorkspaceName(workspaceEntity.getName());
                return authWorkspaceInfo;
            })
            .collect(Collectors.toList());

        shareResourceResp.setWorkspaceList(authWorkspaceInfoList);

        shareResourceResp.setVersionInfoList(getAndSortVersionInfo(shareResourceEntity));
        shareResourceResp.setProjectId(shareResourceEntity.getProjectId());
        shareResourceResp.setTenantId(shareResourceEntity.getTenantId());
        shareResourceResp.setCreator(shareResourceEntity.getCreator());
        shareResourceResp.setShareTime(shareResourceEntity.getCreateTime());
        shareResourceResp.setCreatorId(shareResourceEntity.getCreatorId());

        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(resourceId,
            queryShareResourceInfoByResourceIdQo.getReleaseVersion());
        if (releaseVersion == null) {
            log.error("the release version {} of resource {} is not exist",
                queryShareResourceInfoByResourceIdQo.getReleaseVersion(), resourceId);
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_RELEASE_VERSION_IS_NOT_EXISTED, resourceId,
                queryShareResourceInfoByResourceIdQo.getReleaseVersion());
        }

        if (CommonConstant.WORKFLOW.equals(shareResourceEntity.getResourceType())) {
            WorkflowEntity workflowEntity = workflowMapper.selectByWorkflowId(projectId,
                shareResourceEntity.getWorkspaceId(), resourceId);

            if (workflowEntity == null) {
                log.error("cannot found workflow by resourceId {}", resourceId);
                throw new AgentStudioException(StudioError.WORKSPACE_NOT_EXISTED, resourceId);
            }

            // 列表卡片名称取活表现值，详情与其保持同源（活名优先，快照名仅作初始兜底）
            shareResourceResp.setResourceName(workflowEntity.getName());
            shareResourceResp.setIcon(workflowEntity.getAvatar());
            shareResourceResp.setResourceDescription(workflowEntity.getDescription());
            String workflowDslJson = obsService.downloadObsFile(releaseVersion.getDslPath());
            WorkflowVO workflowVo = JSON.parseObject(workflowDslJson, WorkflowVO.class);
            WorkflowNodeVO startNode = WorkflowUtils.getWorkflowNodeID(CommonConstant.ControllerConstants.INPUT_KEY,
                workflowVo.getNodes());
            // 开始节点的输入为 outputs
            List<WorkflowFieldVO> inputs = startNode == null ? null : startNode.getOutputs();
            if (inputs != null) {
                inputs = inputs.stream().filter(m -> !Strings.CS.equals(SYS, m.getName())).toList();
            }
            shareResourceResp.setWorkflowInputs(inputs);
        } else if (CommonConstant.CONTROLLER.equals(shareResourceEntity.getResourceType())) {
            Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, shareResourceEntity.getWorkspaceId(),
                resourceId);

            if (agent == null) {
                log.error("cannot found agent by resourceId {}", resourceId);
                throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
            }

            // 列表卡片名称取活表现值，详情与其保持同源（活名优先，快照名仅作初始兜底）
            shareResourceResp.setResourceName(agent.getName());
            shareResourceResp.setIcon(agent.getIcon());
            shareResourceResp.setResourceDescription(agent.getDescription());
            String controllerJson = obsService.downloadObsFile(releaseVersion.getDslPath());
            ControllerVO controllerVO = JSONObject.parseObject(controllerJson, ControllerVO.class);
            shareResourceResp.setControllerInputs(controllerVO.getInputs());
        }
        return shareResourceResp;
    }

    /**
     * 查询本空间下共享出去的资源
     */
    @Override
    public ShareResourceListRsp queryShareResourceList(String projectId,
        QueryShareResourceListQo queryShareResourceListQo) {
        log.info("start to query share resource by projectId {}, type {}", projectId,
            queryShareResourceListQo.getResourceType());
        PageHelper.offsetPage(queryShareResourceListQo.getOffset(), queryShareResourceListQo.getLimit());

        List<ShareResourceEntity> shareResourceEntityList = shareResourceMapper.selectSharResourceEntityByWorkspaceId(
            projectId, queryShareResourceListQo.getWorkspaceId(), queryShareResourceListQo.getResourceType(),
            queryShareResourceListQo.getResourceName());

        PageInfo<ShareResourceEntity> pageInfo = new PageInfo<>(shareResourceEntityList);

        if (CollectionUtils.isEmpty(shareResourceEntityList)) {
            return new ShareResourceListRsp().setCount(0).setResourceList(new ArrayList<>());
        }

        ShareResourceListRsp shareResourceListRsp = assembleResourceResponse(projectId,
            queryShareResourceListQo.getResourceType(), shareResourceEntityList);
        shareResourceListRsp.setCount((int) pageInfo.getTotal());
        return shareResourceListRsp;
    }

    /**
     * 查询本空间下被共享的资源
     */
    @Override
    public ShareResourceListRsp querySharedResourceList(String projectId,
        QuerySharedResourceListQo listShareResourcesQo) {
        Integer offset = listShareResourcesQo.getOffset();
        Integer limit = listShareResourcesQo.getLimit();
        PageHelper.offsetPage(offset, limit);

        List<ShareResourceEntity> shareResourceEntityList
            = shareResourceMapper.selectSharedResourceByAuthWorkspaceIdAndType(projectId,
            listShareResourcesQo.getWorkspaceId(), listShareResourcesQo.getResourceType(),
            listShareResourcesQo.getResourceName());

        PageInfo<ShareResourceEntity> pageInfo = new PageInfo<>(shareResourceEntityList);

        if (ObjectUtils.isEmpty(shareResourceEntityList)) {
            return new ShareResourceListRsp().setCount(0).setResourceList(new ArrayList<>());
        }

        ShareResourceListRsp shareResourceListRsp = assembleResourceResponse(projectId,
            listShareResourcesQo.getResourceType(), shareResourceEntityList);

        shareResourceListRsp.setCount((int) pageInfo.getTotal());
        return shareResourceListRsp;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ShareResource",
        description = "取消共享资源",
        resourceId = "resourceId",
        resourceName = ""
    )
    public Boolean cancelShareResource(String projectId, String resourceId, String workspaceId, String resourceType) {
        ShareResourceEntity shareResource = shareResourceMapper.selectShareResourceEntityById(projectId, workspaceId,
            resourceId);
        if (ObjectUtils.isEmpty(shareResource)) {
            log.error("cancelResourceShare: share resource not found.");
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_NOT_FOUNT);
        }

        shareResourceMapper.deleteByPrimaryKey(resourceId);
        shareScopeMapper.deleteByResourceId(resourceId);

        updateResourceShareStatus(resourceId, resourceType, 0);

        mappingMapper.updateShareRelationValidStatusByShareResourceId(resourceId, false);

        return true;
    }

    public List<ShareResourceEntity> queryShareResourceEntityByResourceIdList(List<String> resourceIdList) {
        return shareResourceMapper.selectShareResourceByResourceIds(resourceIdList);
    }

    public ShareResourceEntity queryShareResourceEntityByResourceId(String resourceId) {
        return shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);
    }

    public ShareResourceEntity queryShareResourceEntityByResourceIdAndWorkspaceId(String projectId, String workspaceId,
        String resourceId) {
        return shareResourceMapper.selectShareResourceEntityById(projectId, workspaceId, resourceId);
    }

    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "ShareResource",
        description = "导入共享信息",
        resourceId = "shareInfo.workspaceId",
        resourceName = ""
    )
    public void importShareInfo(String projectId, ShareInfo shareInfo, WfImportDataWrapper wfImportDataWrapper) {
        if (shareInfo == null) {
            return;
        }

        WorkspaceInfo workspaceInfo = workspaceMapper.selectById(projectId, shareInfo.getWorkspaceId());

        if (workspaceInfo == null) {
            return;
        }

        Map<String, String> idToUuid = wfImportDataWrapper.getIdToUuid();
        String resourceId = idToUuid.getOrDefault(shareInfo.getResourceId(), shareInfo.getResourceId());

        importShareResourceInfo(projectId, resourceId, shareInfo);

        importShareResourceScope(projectId, resourceId, shareInfo.getShareScopeEntityList());
    }

    public ShareInfo exportShareInfo(String resourceId) {
        ShareResourceEntity shareResourceEntity = queryShareResourceEntityByResourceId(resourceId);

        if (shareResourceEntity == null) {
            return null;
        }

        ShareInfo shareInfo = new ShareInfo();
        BeanUtils.copyProperties(shareResourceEntity, shareInfo);

        List<ShareScopeEntity> shareScopeEntities = shareScopeMapper.selectShareScopesByResourceId(resourceId);

        shareInfo.setShareScopeEntityList(shareScopeEntities);

        return shareInfo;
    }

    /**
     * 导入共享资源的信息
     *
     * @param projectId 项目ID
     * @param resourceId 资源ID，从UuidMap中获取，如果有主键冲突，已经被替换。
     * @param shareInfo 共享信息
     */
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "ShareResource",
        description = "导入共享资源信息",
        resourceId = "resourceId",
        resourceName = ""
    )
    public void importShareResourceInfo(String projectId, String resourceId, ShareInfo shareInfo) {
        ShareResourceEntity existedShareResourceEntity = queryShareResourceEntityByResourceIdAndWorkspaceId(projectId,
            RequestContextUtils.getRequestWorkspaceId(), resourceId);

        // 如果根据资源对应的ID查询为空，说明环境中不存在该资源的导入信息。直接插入表中即可。
        if (existedShareResourceEntity == null) {
            ShareResourceEntity shareResourceEntity = new ShareResourceEntity();
            BeanUtils.copyProperties(shareInfo, shareResourceEntity);
            shareResourceEntity.setResourceId(resourceId);
            shareResourceEntity.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
            shareResourceEntity.setWorkspaceName(RequestContextUtils.getRequestWorkspaceName());
            shareResourceEntity.setCreator(RequestContextUtils.getRequestUserName());
            shareResourceEntity.setUpdater(RequestContextUtils.getRequestUserName());
            shareResourceEntity.setCreatorId(RequestContextUtils.getRequestUserId());
            shareResourceEntity.setUpdaterId(RequestContextUtils.getRequestUserId());
            shareResourceMapper.insert(shareResourceEntity);
            return;
        }

        // 如果不为空，则说明已经导入过，对导入信息进行更新即可。
        existedShareResourceEntity.setResourceName(shareInfo.getResourceName());
        existedShareResourceEntity.setVersionList(shareInfo.getVersionList());
        shareResourceMapper.updateShareResourceEntity(existedShareResourceEntity);
    }

    /**
     * 导入共享资源的授权范围
     *
     * @param projectId 项目ID
     * @param resourceId 资源ID，从UuidMap中获取，如果有主键冲突，已经被替换。
     * @param shareScopeEntityList 资源的共享范围
     */
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "ShareResource",
        description = "导入共享资源授权范围",
        resourceId = "resourceId",
        resourceName = ""
    )
    public void importShareResourceScope(String projectId, String resourceId,
        List<ShareScopeEntity> shareScopeEntityList) {
        if (CollectionUtils.isEmpty(shareScopeEntityList)) {
            return;
        }

        if (SHARE_WITH_ALL_WORKSPACE.equals(shareScopeEntityList.get(0).getWorkspaceId())) {
            shareScopeMapper.deleteByResourceId(resourceId);
            ShareScopeEntity shareScopeEntity = shareScopeEntityList.get(0);
            shareScopeEntity.setId(UuidUtils.getUUID());
            shareScopeEntity.setResourceId(resourceId);
            shareScopeMapper.insert(shareScopeEntity);
            return;
        }

        List<WorkspaceEntity> workspaceEntityList = workspaceMapper.selectWorkspaceListByDomainId(projectId,
            RequestContextUtils.getRequestUserDomainId());

        Set<String> currentDomainWorkspaceIdSet = workspaceEntityList.stream()
            .map(WorkspaceEntity::getId)
            .collect(Collectors.toSet());

        List<ShareScopeEntity> existedShareScopeListByResourceId = shareScopeMapper.selectShareScopesByResourceId(
            resourceId);

        Set<String> existedShareWorkspaceSetByResourceId = existedShareScopeListByResourceId.stream()
            .map(ShareScopeEntity::getWorkspaceId)
            .collect(Collectors.toSet());

        for (ShareScopeEntity shareScopeEntity : shareScopeEntityList) {
            String workspaceId = shareScopeEntity.getWorkspaceId();
            // 如果当前租户下 不存在导入的workspaceId,不导入该授权范围
            if (!currentDomainWorkspaceIdSet.contains(workspaceId)) {
                continue;
            }

            if (workspaceId.equals(RequestContextUtils.getRequestWorkspaceId())) {
                continue;
            }

            if (existedShareWorkspaceSetByResourceId.contains(workspaceId)) {
                continue;
            }

            shareScopeEntity.setId(UuidUtils.getUUID());
            shareScopeEntity.setResourceId(resourceId);
            shareScopeMapper.insert(shareScopeEntity);
        }
    }

    /**
     * 如果导出的数据携带导入的数据，则要对共享资源范围进行校验
     *
     * @param shareResourceReferenceList 共享范围列表
     * @param targetWorkspaceId 导入的空间ID
     */
    public void validateShareReferences(List<MappingEntity> shareResourceReferenceList, String targetWorkspaceId) {
        if (CollectionUtils.isEmpty(shareResourceReferenceList)) {
            return;
        }

        for (MappingEntity mappingEntity : shareResourceReferenceList) {
            String resourceId = mappingEntity.getResourceId();
            ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(
                pluginAdapter.getPluginId(resourceId));

            // 如果导入的资源引用了共享的资源，则必须要求共享资源在环境中已经存在
            if (shareResourceEntity == null) {
                log.error("{} not share", resourceId);
                throw new AgentStudioException(StudioError.SHARE_RESOURCE_NOT_FOUNT);
            }

            // 共享的资源存在，需要校验是否在授权范围里面
            List<ShareScopeEntity> shareScopeEntityList = shareScopeMapper.selectShareScopesByResourceId(
                pluginAdapter.getPluginId(resourceId));

            if (CollectionUtils.isEmpty(shareScopeEntityList)) {
                log.error("the share scope of resourceId {} is empty", resourceId);
                throw new AgentStudioException(StudioError.CURRENT_WORKSPACE_IS_NOT_IN_SHARE_SCOPE);
            }

            // 如果是授权给全部空间，则不需要校验
            if (SHARE_WITH_ALL_WORKSPACE.equals(shareScopeEntityList.get(0).getWorkspaceId())) {
                return;
            }

            Set<String> sharedWorkspaceSet = shareScopeEntityList.stream()
                .map(ShareScopeEntity::getWorkspaceId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

            String originalWorkspaceId = shareResourceEntity.getWorkspaceId();

            if (!sharedWorkspaceSet.contains(targetWorkspaceId) && !originalWorkspaceId.equals(
                RequestContextUtils.getRequestWorkspaceId())) {
                log.error("the current resource {} is not in share scope list", resourceId);
                throw new AgentStudioException(StudioError.CURRENT_WORKSPACE_IS_NOT_IN_SHARE_SCOPE);
            }
        }
    }

    public boolean checkWorkspaceAuthByResourceOrNot(String workspaceId, String resourceId) {
        ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);

        if (shareResourceEntity == null) {
            return false;
        }

        // 如果资源是共享的，判断当前工作空间是否在授权范围内。
        List<ShareScopeEntity> shareScopeEntities = shareScopeMapper.selectShareScopesByResourceId(resourceId);
        Set<String> authWorkspaceIdSet = shareScopeEntities.stream()
            .map(ShareScopeEntity::getWorkspaceId)
            .collect(Collectors.toSet());

        if (authWorkspaceIdSet.contains(SHARE_WITH_ALL_WORKSPACE)) {
            return true;
        }

        if (!authWorkspaceIdSet.contains(workspaceId)) {
            log.error("current workspace {} is not authorized by resource {}", workspaceId, resourceId);
            return false;
        }
        return true;
    }

    public ShareResourceEntity queryShareResourceEntityByResourceIdAndVersionId(String resourceId,
        String authWorkspaceId, String versionId) {
        if (StringUtils.isBlank(versionId)) {
            return null;
        }

        ShareScopeEntity shareScopeEntity = shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(resourceId,
            authWorkspaceId);

        if (shareScopeEntity == null) {
            return null;
        }

        ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);

        if (!shareResourceEntity.getVersionList().contains(versionId)) {
            return null;
        }
        return shareResourceEntity;
    }

    public void checkResourceSharedOrNot(String projectId, String resourceId) {
        if (shareResourceMapper.countResourceByResourceId(projectId, resourceId) > 0) {
            log.error("the resource has been shared,you can't delete it");
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY);
        }
    }

    /**
     * 校验资源的指定版本是否已共享到资产广场，若已共享则拒绝删除。
     * <p>与 {@link #checkResourceSharedOrNot(String, String)} 资源级校验对应，本方法是版本级校验，
     * 供工作流/智能体/插件版本删除时复用，与 AgentManagementService#deleteAgentVersion 的校验语义一致。
     *
     * @param resourceId 资源ID（agentId / workflowId / pluginId 等）
     * @param versionId  待删除的版本ID
     */
    public void checkVersionSharedOrNot(String resourceId, String versionId) {
        if (StringUtils.isBlank(resourceId) || StringUtils.isBlank(versionId)) {
            return;
        }
        ShareResourceEntity shareResource = shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);
        if (ObjectUtils.isNotEmpty(shareResource) && StringUtils.isNotEmpty(shareResource.getVersionList())
            && shareResource.getVersionList().contains(versionId)) {
            log.error("the resource version [{}] of resource [{}] has been shared, you can't delete it",
                versionId, resourceId);
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY);
        }
    }

    /**
     * 创建或者更新共享资源的授权范围
     *
     * @param resourceId 资源ID
     * @param resourceType 资源类型
     * @param authWorkspaceIdList 授权的空间ID列表
     */
    private void createOrUpdateShareResourceScope(String resourceId, String resourceType,
        List<String> authWorkspaceIdList) {
        shareScopeMapper.deleteByResourceId(resourceId);
        if (SHARE_WITH_ALL_WORKSPACE.equals(authWorkspaceIdList.get(0))) {
            ShareScopeEntity shareScopeEntity = new ShareScopeEntity().setId(UuidUtils.getUUID())
                .setResourceId(resourceId)
                .setResourceType(resourceType)
                .setWorkspaceId(SHARE_WITH_ALL_WORKSPACE)
                .setTenantId(RequestContextUtils.getRequestUserDomainId())
                .setProjectId(RequestContextUtils.getRequestProjectId());
            shareScopeMapper.insert(shareScopeEntity);
            return;
        }

        List<ShareScopeEntity> scopeEntitiesNew = new ArrayList<>();
        authWorkspaceIdList.forEach(authWorkspaceId -> {
            if (authWorkspaceId.equals(RequestContextUtils.getRequestWorkspaceId())) {
                log.error("the auth list contain current workspace {}", RequestContextUtils.getRequestWorkspaceId());
                throw new AgentStudioException(StudioError.CANNOT_SHARE_RESOURCE_TO_SELF_WORKSPACE);
            }
            ShareScopeEntity shareScopeEntity = new ShareScopeEntity().setId(UuidUtils.getUUID())
                .setResourceId(resourceId)
                .setResourceType(resourceType)
                .setWorkspaceId(authWorkspaceId)
                .setProjectId(RequestContextUtils.getRequestProjectId())
                .setTenantId(RequestContextUtils.getRequestUserDomainId());

            scopeEntitiesNew.add(shareScopeEntity);
        });

        shareScopeMapper.batchInsert(scopeEntitiesNew);
    }

    private void updateResourceShareStatus(String resourceId, String resourceType, int status) {
        if (ShareResourceInfo.ResourceTypeEnum.CONTROLLER.toString().equals(resourceType)) {
            agentMapper.updateAgentShareStatus(resourceId, status);
        } else if (ShareResourceInfo.ResourceTypeEnum.WORKFLOW.toString().equals(resourceType)) {
            workflowMapper.updateWorkflowShareStatus(resourceId, status);
        } else if (ShareResourceInfo.ResourceTypeEnum.PLUGIN.toString().equals(resourceType)) {
            pluginMapper.updatePluginShareStatus(resourceId, status);
        } else if (ShareResourceInfo.ResourceTypeEnum.MCP.toString().equals(resourceType)) {
            mcpServiceDao.updateMcpShareStatus(resourceId, status);
        } else if (ShareResourceInfo.ResourceTypeEnum.PROMPT.toString().equals(resourceType)) {
            pePromptTemplateMapper.updatePromptShareStatus(resourceId, status);
        }
    }

    private ShareResourceListRsp assembleResourceResponse(String projectId, String resourceType,
        List<ShareResourceEntity> shareResourceEntityList) {
        ShareResourceListRsp shareResourceListRsp = new ShareResourceListRsp();
        switch (resourceType) {
            case CommonConstant.CONTROLLER -> {
                List<ShareResourceInfo> controllerShareResourceInfoList = queryControllerResource(projectId,
                    shareResourceEntityList);
                shareResourceListRsp.setResourceList(controllerShareResourceInfoList);
                return shareResourceListRsp;
            }
            case CommonConstant.WORKFLOW -> {
                List<ShareResourceInfo> workflowShareResourceInfoList = queryWorkflowResource(projectId,
                    shareResourceEntityList);
                shareResourceListRsp.setResourceList(workflowShareResourceInfoList);
                return shareResourceListRsp;
            }
            case PLUGIN_TYPE -> {
                List<ShareResourceInfo> shareResourceInfos = queryPluginResource(shareResourceEntityList);
                shareResourceListRsp.setResourceList(shareResourceInfos);
                return shareResourceListRsp;
            }
            case MCP_TYPE -> {
                List<ShareResourceInfo> mcpShareResourceInfoList = queryMcpResource(projectId, shareResourceEntityList);
                shareResourceListRsp.setResourceList(mcpShareResourceInfoList);
                return shareResourceListRsp;
            }
            case PROMPT -> {
                List<ShareResourceInfo> promptResourceInfoList = queryPromptResource(projectId, shareResourceEntityList);
                shareResourceListRsp.setResourceList(promptResourceInfoList);
                return shareResourceListRsp;
            }
            case ALL -> {
                List<ShareResourceInfo> controllerShareResourceInfoList = queryControllerResource(projectId,
                    shareResourceEntityList);
                List<ShareResourceInfo> workflowShareResourceInfoList = queryWorkflowResource(projectId,
                    shareResourceEntityList);

                shareResourceListRsp.setResourceList(
                    Stream.concat(controllerShareResourceInfoList.stream(), workflowShareResourceInfoList.stream())
                        .toList());
                return shareResourceListRsp;
            }
            default -> {
                log.error("validResourceParam: invalid resource type");
                throw new AgentStudioException(StudioError.RESOURCE_TYPE_NOT_VALID);
            }
        }
    }

    private List<ShareResourceInfo> queryPromptResource(String projectId, List<ShareResourceEntity> shareResourceEntityList) {
        List<ShareResourceInfo> shareResourceInfos = new ArrayList<>();
        if (CollectionUtils.isEmpty(shareResourceEntityList)) {
            return shareResourceInfos;
        }
        List<String> promptIds = shareResourceEntityList.stream()
            .map(ShareResourceEntity::getResourceId)
            .toList();

        List<PePromptTemplate> pePromptTemplates = pePromptTemplateMapper.batchQueryTemplateByIds(promptIds, projectId);

        Map<String, PePromptTemplate> pePromptTemplateMap = pePromptTemplates.stream()
            .collect(Collectors.toMap(PePromptTemplate::getId, pePromptTemplate -> pePromptTemplate));

        shareResourceEntityList.forEach(shareResourceEntity -> {
            PePromptTemplate pePromptTemplate = pePromptTemplateMap.get(shareResourceEntity.getResourceId());

            ShareResourceInfo shareResourceInfo = new ShareResourceInfo().setResourceId(
                    shareResourceEntity.getResourceId())
                .setCreator(shareResourceEntity.getCreator())
                .setResourceType(ShareResourceInfo.ResourceTypeEnum.fromValue(shareResourceEntity.getResourceType()))
                .setVersionInfoList(null)
                .setWorkspaceId(shareResourceEntity.getWorkspaceId())
                .setWorkspaceName(shareResourceEntity.getWorkspaceName())
                .setResourceNameCh(pePromptTemplate.getName())
                .setResourceDesc(pePromptTemplate.getDescription());

            Map<String, Object> extendAttribute = new HashMap<>();
            extendAttribute.put("content", pePromptTemplate.getContent());
            shareResourceInfo.setExtendAttribute(extendAttribute);

            shareResourceInfos.add(shareResourceInfo);
        });
        return shareResourceInfos;
    }

    private List<ShareResourceInfo> queryMcpResource(String projectId, List<ShareResourceEntity> shareResourceEntityList) {
        List<ShareResourceInfo> shareResourceInfos = new ArrayList<>();
        if (CollectionUtils.isEmpty(shareResourceEntityList)) {
            return shareResourceInfos;
        }
        List<String> mcpIds = shareResourceEntityList.stream()
            .map(ShareResourceEntity::getResourceId)
            .collect(Collectors.toList());
        List<McpServiceEntity> mcpServiceEntities = mcpServiceDao.listMcpServiceByIdAndProjectId(mcpIds, projectId);

        Map<String, McpServiceEntity> mcpServiceEntityMap = mcpServiceEntities.stream()
            .collect(Collectors.toMap(McpServiceEntity::getId, mcpServiceEntity -> mcpServiceEntity));

        shareResourceEntityList.forEach(shareResourceEntity -> {
            McpServiceEntity mcpServiceEntity = mcpServiceEntityMap.get(shareResourceEntity.getResourceId());

            ShareResourceInfo shareResourceInfo = new ShareResourceInfo().setResourceId(
                    shareResourceEntity.getResourceId())
                .setCreator(shareResourceEntity.getCreator())
                .setResourceType(ShareResourceInfo.ResourceTypeEnum.fromValue(shareResourceEntity.getResourceType()))
                .setVersionInfoList(null)
                .setWorkspaceId(shareResourceEntity.getWorkspaceId())
                .setWorkspaceName(shareResourceEntity.getWorkspaceName())
                .setResourceNameCh(mcpServiceEntity.getName())
                .setResourceNameEn(mcpServiceEntity.getNameEn())
                .setResourceDesc(mcpServiceEntity.getDescription())
                .setResourceIcon(mcpServiceEntity.getIcon());

            shareResourceInfos.add(shareResourceInfo);
        });
        return shareResourceInfos;
    }

    private List<ShareResourceInfo> queryPluginResource(List<ShareResourceEntity> shareResourceEntityList) {
        List<ShareResourceInfo> shareResourceInfos = new ArrayList<>();
        if (CollectionUtils.isEmpty(shareResourceEntityList)) {
            return shareResourceInfos;
        }
        shareResourceEntityList.forEach(shareResourceEntity -> {
            List<ResourceVersionInfo> versionInfos = JSONObject.parseObject(shareResourceEntity.getVersionList(),
                new TypeReference<>() { });
            if (CollectionUtils.isEmpty(versionInfos)) {
                return;
            }
            try {
                // 共享快照中的版本可能已被删除或从未导入（快照不随发版/删版同步），
                // 遍历取第一个真实存在的版本解析插件实体，避免固定取快照第一个版本导致
                // 该版本失效时整张卡片被吞掉、列表与计数口径不一致
                PluginEntity plugin = null;
                for (ResourceVersionInfo versionInfo : versionInfos) {
                    if (versionInfo == null || StringUtils.isEmpty(versionInfo.getVersionId())) {
                        continue;
                    }
                    try {
                        plugin = pluginBase.getPluginEntityByVersion(shareResourceEntity.getResourceId(),
                            versionInfo.getVersionId());
                        break;
                    } catch (Exception e) {
                        log.info("share version not available, resourceId={}, versionId={}",
                            shareResourceEntity.getResourceId(), versionInfo.getVersionId());
                    }
                }
                if (plugin == null) {
                    // 快照版本全部失效，兜底用插件表现状渲染基本信息卡，保证列表与计数口径一致
                    plugin = pluginMapper.selectByPrimaryKey(shareResourceEntity.getResourceId(), null);
                }
                if (plugin == null) {
                    log.warn("query plugin failed, resourceId={}", shareResourceEntity.getResourceId());
                    return;
                }
                ShareResourceInfo shareResourceInfo = new ShareResourceInfo().setResourceId(
                        shareResourceEntity.getResourceId())
                    .setCreator(shareResourceEntity.getCreator())
                    .setResourceType(ShareResourceInfo.ResourceTypeEnum.fromValue(shareResourceEntity.getResourceType()))
                    .setVersionInfoList(getAndSortVersionInfo(shareResourceEntity))
                    .setWorkspaceId(shareResourceEntity.getWorkspaceId())
                    .setWorkspaceName(shareResourceEntity.getWorkspaceName())
                    .setResourceNameCh(plugin.getPluginChineseName())
                    .setResourceNameEn(plugin.getPluginDisplayName())
                    .setResourceDesc(plugin.getPluginDesc())
                    .setResourceIcon(plugin.getIcon());

                Map<String, Object> extendAttribute = new HashMap<>();
                extendAttribute.put("request_info", JSONObject.parseObject(plugin.getRequestInfo(), Object.class));
                shareResourceInfo.setExtendAttribute(extendAttribute);
                shareResourceInfos.add(shareResourceInfo);
            } catch (Exception e) {
                log.warn("query plugin failed, resourceId={}", shareResourceEntity.getResourceId());
            }
        });
        return shareResourceInfos;
    }

    private List<ShareResourceInfo> queryControllerResource(String projectId,
        List<ShareResourceEntity> shareResourceEntityList) {
        List<ShareResourceInfo> controllerShareResourceInfoList = new ArrayList<>();

        List<String> controllerIdList = shareResourceEntityList.stream()
            .filter(shareResourceEntity -> CommonConstant.CONTROLLER.equals(shareResourceEntity.getResourceType()))
            .map(ShareResourceEntity::getResourceId)
            .toList();

        if (CollectionUtils.isEmpty(controllerIdList)) {
            return controllerShareResourceInfoList;
        }

        List<Agent> controllerList = agentMapper.selectByAgentIds(projectId, CommonConstant.CONTROLLER,
            controllerIdList);

        if (CollectionUtils.isEmpty(controllerList)) {
            return controllerShareResourceInfoList;
        }

        Map<String, Agent> controllerResourceMap = controllerList.stream()
            .collect(Collectors.toMap(Agent::getAgentId, agent -> agent));

        for (ShareResourceEntity shareResourceEntity : shareResourceEntityList) {

            if (!ShareResourceInfo.ResourceTypeEnum.CONTROLLER.toString()
                .equals(shareResourceEntity.getResourceType())) {
                continue;
            }

            Agent agent = controllerResourceMap.get(shareResourceEntity.getResourceId());

            if (agent == null) {
                log.info("controllerResource not found, resourceId={}", shareResourceEntity.getResourceId());
                continue;
            }

            ShareResourceInfo shareResourceInfo = new ShareResourceInfo().setResourceId(
                    shareResourceEntity.getResourceId())
                .setResourceType(ShareResourceInfo.ResourceTypeEnum.fromValue(shareResourceEntity.getResourceType()))
                .setVersionInfoList(getAndSortVersionInfo(shareResourceEntity))
                .setWorkspaceId(shareResourceEntity.getWorkspaceId())
                .setWorkspaceName(shareResourceEntity.getWorkspaceName())
                .setResourceNameCh(agent.getName())
                .setResourceNameEn("")
                .setResourceDesc(agent.getDescription())
                .setResourceIcon(agent.getIcon())
                .setCreator(shareResourceEntity.getCreator())
                .setType(agent.getType());

            controllerShareResourceInfoList.add(shareResourceInfo);
        }

        return controllerShareResourceInfoList;
    }

    private List<ShareResourceInfo> queryWorkflowResource(String projectId,
        List<ShareResourceEntity> shareResourceEntityList) {
        List<ShareResourceInfo> workflowShareResourceInfoList = new ArrayList<>();

        if (CollectionUtils.isEmpty(shareResourceEntityList)) {
            return workflowShareResourceInfoList;
        }

        List<String> workflowIdList = shareResourceEntityList.stream()
            .filter(shareResourceEntity -> CommonConstant.WORKFLOW.equals(shareResourceEntity.getResourceType()))
            .map(ShareResourceEntity::getResourceId)
            .toList();

        if (CollectionUtils.isEmpty(workflowIdList)) {
            return workflowShareResourceInfoList;
        }

        List<WorkflowEntity> workflowResourceList = workflowMapper.selectByWorkflowIds(projectId, null, workflowIdList);

        if (CollectionUtils.isEmpty(workflowResourceList)) {
            return workflowShareResourceInfoList;
        }

        Map<String, WorkflowEntity> workflowResourceMap = workflowResourceList.stream()
            .collect(Collectors.toMap(WorkflowEntity::getId, workflowEntity -> workflowEntity));

        shareResourceEntityList.forEach(shareResourceEntity -> {
            if (!ShareResourceInfo.ResourceTypeEnum.WORKFLOW.toString().equals(shareResourceEntity.getResourceType())) {
                return;
            }

            WorkflowEntity workflowEntity = workflowResourceMap.get(shareResourceEntity.getResourceId());
            if (workflowEntity == null) {
                log.warn("workflowResource not found, resourceId={}", shareResourceEntity.getResourceId());
                return;
            }

            ShareResourceInfo shareResourceInfo = new ShareResourceInfo().setResourceId(
                    shareResourceEntity.getResourceId())
                .setResourceType(ShareResourceInfo.ResourceTypeEnum.fromValue(shareResourceEntity.getResourceType()))
                .setVersionInfoList(getAndSortVersionInfo(shareResourceEntity))
                .setWorkspaceId(shareResourceEntity.getWorkspaceId())
                .setWorkspaceName(shareResourceEntity.getWorkspaceName())
                .setResourceNameCh(workflowEntity.getName())
                .setResourceNameEn(workflowEntity.getCode())
                .setResourceDesc(workflowEntity.getDescription())
                .setResourceIcon(workflowEntity.getAvatar())
                .setCreator(shareResourceEntity.getCreator())
                .setType(workflowEntity.getWorkflowType());

            workflowShareResourceInfoList.add(shareResourceInfo);
        });

        return workflowShareResourceInfoList;
    }

    private List<ResourceVersionInfo> getAndSortVersionInfo(ShareResourceEntity shareResourceEntity) {
        List<ResourceVersionInfo> versionInfoList = JSONObject.parseObject(shareResourceEntity.getVersionList(),
            new TypeReference<>() { });
        // 按照版本号从大到小排序（需要实现 Comparable 接口或使用 Comparator）
        versionInfoList.sort(Comparator.comparing(ResourceVersionInfo::getVersionId).reversed());
        return versionInfoList;
    }

    private String validResourceParam(String projectId, String workspaceId, ShareResourceRequestInfo body,
        List<ResourceVersionInfo> versionInfos) {
        // 校验是否已经引用共享资源，已经引用的元素不允许再共享
        List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(body.getResourceId(), null, null,
            null);
        List<MappingEntity> shareMap = Optional.ofNullable(mappingEntities)
            .orElse(new ArrayList<>())
            .stream()
            .filter(mappingEntity -> body.getVersionList().contains(mappingEntity.getAppVersion()))
            .filter(mappingEntity -> ReferenceTypeEnum.SHARE.getValue().equals(mappingEntity.getReferenceType()))
            .toList();
        if (ObjectUtils.isNotEmpty(shareMap)) {
            log.error(
                "Objects with referenced resources cannot be shared, projectId = {}, workspaceId = {}, resourceId = {}",
                projectId, workspaceId, body.getResourceId());
            throw new AgentStudioException(StudioError.EXIST_SHARE_REFERENCE);
        }

        checkShareResourceScopeValidOrNot(projectId, workspaceId, body.getAuthWorkspaceIdList());

        switch (body.getResourceType()) {
            case CONTROLLER -> {
                Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, body.getResourceId());

                // 如果Agent对象为空，记录错误日志并抛出异常
                if (agent == null) {
                    log.error("agent does not exist, projectId = {}, workspaceId = {}, agentId = {}", projectId,
                        workspaceId, body.getResourceId());
                    throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
                }
                // 校验版本存在性
                checkAgentOrWorkflowVersion(projectId, workspaceId, body, versionInfos);

                // 返回trace_id
                return agent.getTraceId();
            }
            case WORKFLOW -> {
                WorkflowEntity workflowEntity = workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId,
                    body.getResourceId());

                // 如果workflow对象为空，记录错误日志并抛出异常
                if (workflowEntity == null) {
                    log.error("workflow does not exist, projectId = {}, workspaceId = {}, workflowId = {}", projectId,
                        workspaceId, body.getResourceId());
                    throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
                }

                // 校验版本存在性
                checkAgentOrWorkflowVersion(projectId, workspaceId, body, versionInfos);

                // 返回trace_id
                return workflowEntity.getTraceId();
            }
            case PLUGIN -> {
                PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(body.getResourceId(), projectId,
                    workspaceId);
                if (Objects.isNull(pluginEntity)) {
                    log.error("Plugin {} projectId {} workspaceId {} does not exist.", body.getResourceId(), projectId,
                        workspaceId);
                    throw new AgentStudioException(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, body.getResourceId(),
                        projectId, workspaceId);
                }

                // 校验版本存在性
                checkAgentOrWorkflowVersion(projectId, workspaceId, body, versionInfos);
                return pluginEntity.getTraceId();
            }
            case MCP -> {
                String tenantId = RequestContextUtils.getRequestUserDomainId();
                McpServiceEntity serviceEntity = mcpServiceDao.selectById(body.getResourceId(), tenantId,
                    CommonUtil.getDeptCode(), workspaceId);
                if (Objects.isNull(serviceEntity)) {
                    log.error("MCP {} projectId {} workspaceId {} does not exist.", body.getResourceId(), projectId,
                        workspaceId);
                    throw new AgentStudioException(StudioError.MCP_SERVER_ID_NOT_EXIST, body.getResourceId());
                }
                return serviceEntity.getTraceId();
            }
            case PROMPT -> {
                PePromptTemplate pePromptTemplate = pePromptTemplateMapper.queryTemplateDetailById(body.getResourceId(), projectId, workspaceId);
                if (Objects.isNull(pePromptTemplate)) {
                    log.error("PROMPT {} projectId {} workspaceId {} does not exist.", body.getResourceId(), projectId,
                        workspaceId);
                    throw new AgentStudioException(StudioError.PROMPT_ID_IS_NOT_EXISTED, body.getResourceId());
                }
                return pePromptTemplate.getId();
            }
            default -> {
                // 无效作用域，记录错误日志并抛出异常
                log.error("validResourceParam: invalid resource type");
                throw new AgentStudioException(StudioError.RESOURCE_TYPE_NOT_VALID);
            }
        }
    }

    private void validateWorkspaceShareByResourceOrNot(ShareResourceEntity shareResourceEntity) {
        if (shareResourceEntity.getWorkspaceId().equals(RequestContextUtils.getRequestWorkspaceId())) {
            return;
        }

        List<ShareScopeEntity> shareScopeEntities = shareScopeMapper.selectShareScopesByResourceId(
            shareResourceEntity.getResourceId());

        if (CollectionUtils.isEmpty(shareScopeEntities)) {
            log.error("current workspace {} is not auth by resource {}", RequestContextUtils.getRequestWorkspaceId(),
                shareResourceEntity.getResourceId());
            throw new AgentStudioException(StudioError.CURRENT_WORKSPACE_IS_NOT_AUTH);
        }

        if (SHARE_WITH_ALL_WORKSPACE.equals(shareScopeEntities.get(0).getWorkspaceId())) {
            return;
        }

        Set<String> authWorkspaceIdSet = shareScopeEntities.stream()
            .map(ShareScopeEntity::getWorkspaceId)
            .collect(Collectors.toSet());
        if (!authWorkspaceIdSet.contains(RequestContextUtils.getRequestWorkspaceId())) {
            log.error("current workspace {} is not auth by resource {}", RequestContextUtils.getRequestWorkspaceId(),
                shareResourceEntity.getResourceId());
            throw new AgentStudioException(StudioError.CURRENT_WORKSPACE_IS_NOT_AUTH);
        }
    }

    private void checkShareResourceScopeValidOrNot(String projectId, String workspaceId,
        List<String> authWorkspaceIdList) {
        if (SHARE_WITH_ALL_WORKSPACE.equals(authWorkspaceIdList.get(0))) {
            return;
        }

        // 授权的空间，必须是同租户下面的空间
        List<WorkspaceEntity> workspaceEntityList = workspaceMapper.getWorkspaceByTenantId(
            RequestContextUtils.getRequestUserDomainId());

        Set<String> currentDomainWorkspaceIdSet = workspaceEntityList.stream()
            .map(WorkspaceEntity::getId)
            .collect(Collectors.toSet());

        for (String authWorkspaceId : authWorkspaceIdList) {
            if (!currentDomainWorkspaceIdSet.contains(authWorkspaceId)) {
                log.error("authWorkspaceId is invalid, projectId = {}, workspaceId = {}, authWorkspaceIdList = {}",
                    projectId, workspaceId,
                    ObjectUtils.isNotEmpty(authWorkspaceIdList) ? authWorkspaceIdList.toString() : StringUtils.EMPTY);
                throw new AgentStudioException(StudioError.AUTH_WORKSPACE_NOT_FOUNT);
            }
        }
    }

    private void checkAgentOrWorkflowVersion(String projectId, String workspaceId, ShareResourceRequestInfo body,
        List<ResourceVersionInfo> versionInfos) {
        List<ReleaseVersion> versionList = releaseVersionMapper.selectByAppId(body.getResourceId());

        List<ResourceVersionInfo> resourceVersions = versionList.stream()
            .map(release -> new ResourceVersionInfo().setVersionId(release.getVersionId())
                .setVersionName(release.getVersionName()))
            .toList();

        resourceVersions.forEach(version -> {
            if (body.getVersionList().contains(version.getVersionId())) {
                versionInfos.add(version);
            }
        });

        List<String> versions = versionList.stream().map(ReleaseVersion::getVersionId).toList();
        boolean versionIsValid = isListIncluded(body.getVersionList(), versions);

        // 不存在抛出异常 Agent
        if (!versionIsValid && body.getResourceType() == ShareResourceRequestInfo.ResourceTypeEnum.CONTROLLER) {
            log.error("version does not valid, projectId = {}, workspaceId = {}, agentId = {}, versionList = {}",
                projectId, workspaceId, body.getResourceId(), body.getVersionList().toString());
            throw new AgentStudioException(StudioError.AGENT_VERSION_NOT_EXIST);
        }
        // 不存在抛出异常 Workflow
        if (!versionIsValid && body.getResourceType() == ShareResourceRequestInfo.ResourceTypeEnum.WORKFLOW) {
            log.error("version does not valid, projectId = {}, workspaceId = {}, workflowId = {}, versionList = {}",
                projectId, workspaceId, body.getResourceId(), body.getVersionList().toString());
            throw new AgentStudioException(StudioError.WORKFLOW_VERSION_NOT_FOUND);
        }
        // 不存在抛出异常 plugin
        if (!versionIsValid && body.getResourceType() == ShareResourceRequestInfo.ResourceTypeEnum.PLUGIN) {
            log.error("version does not valid, projectId = {}, workspaceId = {}, workflowId = {}, versionList = {}",
                projectId, workspaceId, body.getResourceId(), body.getVersionList().toString());
            throw new AgentStudioException(StudioError.TOOL_VERSION_NOT_EXIST, body.getResourceId(),
                body.getVersionList().toString());
        }
    }

    /**
     * 判断source列表是否被包含在target列表中
     *
     * @param source 被检查需要包含的列表
     * @param target 目标列表
     * @return 若全部包含则返回 true，否则返回 false
     */
    public boolean isListIncluded(List<String> source, List<String> target) {
        // 版本列表为空
        if (source == null || source.isEmpty() || target == null || target.isEmpty()) {
            return false;
        }

        // 将目标列表转为 HashSet，利用 O(1) 查找效率
        Set<String> targetSet = new HashSet<>(target);
        // 判断源列表的所有元素是否都在目标集合中
        return targetSet.containsAll(source);
    }
}

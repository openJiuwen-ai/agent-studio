/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.workspace;

import com.openjiuwen.studio.agent.common.annotation.DistributedLock;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.entity.ResourceMultipartFile;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.common.utils.UuidUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.CreateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.ExternalMappingInfo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.MemberRole;
import com.openjiuwen.studio.agent.manager.dto.QueryWorkspaceQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberInfo;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.enums.ExportModeEnum;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.service.AgentManagementService;
import com.openjiuwen.studio.agent.manager.service.IWorkspaceService;
import com.openjiuwen.studio.agent.manager.service.SkuManageService;
import com.openjiuwen.studio.agent.manager.service.WorkflowManagementService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.support.ResourcePatternResolver;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

/**
 * 项目空间管理实现类
 *
 */
@Slf4j
@Service
public class WorkspaceService implements IWorkspaceService {

    @Resource
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private WorkspaceMappingService workspaceMappingService;

    @Resource
    private WorkspaceMemberService workspaceMemberService;

    @Resource
    private SkuManageService skuManageService;

    @Resource
    private AgentManagementService agentManagementService;

    @Resource
    private WorkflowManagementService workflowManagementService;

    @Resource
    private ResourcePatternResolver resourcePatternResolver;

    @Value("${agent.default-icon}")
    private String workSpaceDefaultIcon;

    @Value("${icon.max-size}")
    private String iconMaxSize;

    @Value("${file.icon-type}")
    private String allowedIconTypeStr;

    @Value("${agent.init-template-enable}")
    private boolean agentInitTemplateEnable;

    @Value("${agent.init-template-path}")
    private String agentInitTemplatePath;

    private Set<String> allowedIconType = new HashSet<>();

    /**
     * 初始化
     */
    @PostConstruct
    public void init() {
        allowedIconType = Arrays.stream(allowedIconTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
    }

    @Override
    @Transactional
    @DistributedLock(prefix = "workspace:create:")
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workspace",
        description = "创建空间",
        resourceId = "-1",
        resourceName = "createWorkspaceReq.name"
    )
    public String createWorkspace(String projectId, CreateWorkspaceReq createWorkspaceReq) {
        log.info("start to create workspace, projectId: {}, body: {}", projectId, createWorkspaceReq);
        validateIcon(createWorkspaceReq.getIcon());

        skuManageService.validateExceededLimitOrNot(CommonConstant.SKU_ATTR_CODE.TEAM_SPACE_COUNT,
            workspaceMapper.countWorkspaceByDomainId(projectId, RequestContextUtils.getRequestUserDomainId()));

        if (workspaceMapper.countWorkspaceEntityByName(projectId, createWorkspaceReq.getName()) > 0) {
            log.error("the workspace name {} is already exist in project {}", createWorkspaceReq.getName(), projectId);
            throw new AgentStudioException(StudioError.WORKSPACE_NAME_REPEAT, createWorkspaceReq.getName());
        }

        String workspaceId = StringUtils.isNotEmpty(createWorkspaceReq.getId())
            ? createWorkspaceReq.getId()
            : UuidUtils.getUUID();

        WorkspaceEntity workspaceEntity = new WorkspaceEntity().setId(workspaceId)
            .setProjectId(projectId)
            .setName(createWorkspaceReq.getName())
            .setDescription(ObjectUtils.isEmpty(createWorkspaceReq.getDescription()) ? "" : createWorkspaceReq.getDescription())
            .setIcon(
                StringUtils.isEmpty(createWorkspaceReq.getIcon()) ? workSpaceDefaultIcon : createWorkspaceReq.getIcon())
            .setTenantId(RequestContextUtils.getRequestUserDomainId())
            .setStatus(CommonConstant.WORKSPACE.STATUS.ENABLE)
            .setType(StringUtils.isEmpty(createWorkspaceReq.getType())
                ? CommonConstant.WORKSPACE.TYPE.TEAM_TYPE
                : createWorkspaceReq.getType())
            .setCreator(RequestContextUtils.getRequestUserName())
            .setCreatorId(RequestContextUtils.getRequestUserId())
            .setCreatedOn(new Date())
            .setUpdater(RequestContextUtils.getRequestUserName())
            .setUpdaterId(RequestContextUtils.getRequestUserId())
            .setUpdatedOn(new Date());

        workspaceMapper.insert(workspaceEntity);
        workspaceMemberService.addWorkspaceMember(workspaceEntity.getId(), RequestContextUtils.getRequestUserId(),
            MemberRole.OWNER.getValue());

        workspaceMappingService.associateWorkspaceRelationWithExternalSystem(workspaceId,
            createWorkspaceReq.getExternalMappingInfo());

        return workspaceEntity.getId();
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Workspace",
        description = "修改空间",
        resourceId = "updateWorkspaceReq.id",
        resourceName = "updateWorkspaceReq.name"
    )
    public WorkspaceInfo updateWorkspace(String projectId, UpdateWorkspaceReq updateWorkspaceReq) {
        WorkspaceInfo workspaceInfo = new WorkspaceInfo();
        validateIcon(updateWorkspaceReq.getIcon());

        WorkspaceEntity existedWorkspaceEntity = workspaceMapper.selectWorkspaceEntityById(projectId,
            updateWorkspaceReq.getId());

        if (existedWorkspaceEntity == null) {
            log.error("the workspace of id {} in projectId {} is not exist", updateWorkspaceReq.getId(), projectId);
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }

        WorkspaceMemberInfo workspaceMemberInfo = workspaceMemberService.queryWorkspaceMemberDetail(projectId,
            RequestContextUtils.getRequestUserId(), updateWorkspaceReq.getId());

        if (workspaceMemberInfo == null || (!MemberRole.OWNER.getValue().equals(workspaceMemberInfo.getRole())
            && !MemberRole.ADMIN.getValue().equals(workspaceMemberInfo.getRole()))) {
            log.error("workspaceMemberInfo is {}", workspaceMemberInfo);
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }

        // 校验工作空间名称是否重复（排除当前正在更新的工作空间）
        if (!existedWorkspaceEntity.getName().equals(updateWorkspaceReq.getName()) 
            && workspaceMapper.countWorkspaceEntityByName(projectId, updateWorkspaceReq.getName()) > 0) {
            log.error("the workspace name {} is already exist in project {}", updateWorkspaceReq.getName(), projectId);
            throw new AgentStudioException(StudioError.WORKSPACE_NAME_REPEAT, updateWorkspaceReq.getName());
        }

        existedWorkspaceEntity.setId(updateWorkspaceReq.getId())
            .setName(updateWorkspaceReq.getName())
            .setDescription(updateWorkspaceReq.getDescription())
            .setIcon(StringUtils.isEmpty(updateWorkspaceReq.getIcon()) ? null : updateWorkspaceReq.getIcon())
            .setUpdater(RequestContextUtils.getRequestUserName())
            .setUpdaterId(RequestContextUtils.getRequestUserId())
            .setUpdatedOn(new Date());
        workspaceMapper.updateByPrimaryKeySelective(existedWorkspaceEntity);

        workspaceMappingService.associateWorkspaceRelationWithExternalSystem(updateWorkspaceReq.getId(),
            updateWorkspaceReq.getExternalMappingInfo());

        BeanUtils.copyProperties(existedWorkspaceEntity, workspaceInfo);

        return workspaceInfo;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Workspace",
        description = "删除空间",
        resourceId = "deleteWorkspaceReq.id",
        resourceName = ""
    )
    public String deleteWorkspace(String projectId, DeleteWorkspaceReq deleteWorkspaceReq) {
        if (deleteWorkspaceReq == null) {
            throw new AgentStudioException(StudioError.PARAMS_IS_REQUIRED);
        }
        WorkspaceMemberInfo workspaceMemberInfo = workspaceMemberService.queryWorkspaceMemberDetail(projectId,
            RequestContextUtils.getRequestUserId(), deleteWorkspaceReq.getId());

        if (workspaceMemberInfo == null || !MemberRole.OWNER.getValue().equals(workspaceMemberInfo.getRole())) {
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }

        WorkspaceInfo workspaceInfo = workspaceMapper.selectById(projectId, deleteWorkspaceReq.getId());

        if (workspaceInfo == null || CommonConstant.WORKSPACE.TYPE.PERSON_TYPE.equals(workspaceInfo.getType())) {
            log.error("user {} no permission to delete workspace {}", RequestContextUtils.getRequestUserId(),
                deleteWorkspaceReq.getId());
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }

        WorkspaceEntity workspaceEntity = new WorkspaceEntity();
        workspaceEntity.setId(deleteWorkspaceReq.getId()).setStatus(CommonConstant.WORKSPACE.STATUS.DISABLE);
        workspaceMemberService.deleteWorkspaceMember(deleteWorkspaceReq.getId(),
            RequestContextUtils.getRequestUserId());
        workspaceMapper.updateByPrimaryKeySelective(workspaceEntity);
        return deleteWorkspaceReq.getId();
    }

    @Override
    public GetWorkspaceListRsp queryWorkspace(String projectId, QueryWorkspaceQo queryWorkspaceQo) {
        log.info("begin get workspace, projectId: {}, userId: {}", projectId, RequestContextUtils.getRequestUserId());

        // scope 为project, 查询project对应的所有团队空间信息
        if ("project".equals(queryWorkspaceQo.getScope())) {
            List<WorkspaceInfo> workspaceInfoList = workspaceMapper.selectWorkspaceWithMappingInfo(projectId,
                queryWorkspaceQo.getSource());
            return new GetWorkspaceListRsp().setCount(workspaceInfoList.size()).setWorkspaceList(workspaceInfoList);
        }

        // scope 为domain, 查询租户内所有团队空间信息
        if ("domain".equals(queryWorkspaceQo.getScope())) {
            List<WorkspaceEntity> workspaceEntityList = workspaceMapper.getWorkspaceByTenantId(
                RequestContextUtils.getRequestUserDomainId());

            List<WorkspaceInfo> workspaceList = new ArrayList<>();

            WorkspaceInfo workspaceInfo;
            for (WorkspaceEntity workspaceEntity : workspaceEntityList) {
                workspaceInfo = new WorkspaceInfo();
                BeanUtils.copyProperties(workspaceEntity, workspaceInfo);
                workspaceList.add(workspaceInfo);
            }
            return new GetWorkspaceListRsp().setCount(workspaceList.size()).setWorkspaceList(workspaceList);
        }

        List<WorkspaceInfo> userJoinedWorkspaceInfoList = new ArrayList<>();

        // scope 为 user, 查询当前登录的用户加入了哪些空间
        List<WorkSpaceMemberEntity> userJoinedWorkspaceMemberList
            = workspaceMemberService.queryAllWorkSpaceInfoByIamUserId(RequestContextUtils.getRequestUserId());
        Map<String, WorkSpaceMemberEntity> workSpaceMemberMap = userJoinedWorkspaceMemberList.stream()
            .collect(Collectors.toMap(WorkSpaceMemberEntity::getWorkspaceId, Function.identity()));

        List<String> userJoinedWorkspaceIdList = new ArrayList<>(workSpaceMemberMap.keySet());

        List<WorkspaceEntity> workspaceEntityList = workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(projectId,
            userJoinedWorkspaceIdList, queryWorkspaceQo.getType());

        WorkspaceInfo workspaceInfo;
        for (WorkspaceEntity workspaceEntity : workspaceEntityList) {
            workspaceInfo = new WorkspaceInfo();
            BeanUtils.copyProperties(workspaceEntity, workspaceInfo);
            workspaceInfo.setRole(workSpaceMemberMap.get(workspaceEntity.getId()).getRole());
            userJoinedWorkspaceInfoList.add(workspaceInfo);
        }

        return new GetWorkspaceListRsp().setCount(userJoinedWorkspaceInfoList.size())
            .setWorkspaceList(userJoinedWorkspaceInfoList);
    }

    @Override
    public WorkspaceInfo queryWorkspaceById(String projectId, String workspaceId) {
        WorkspaceInfo workspaceInfo = new WorkspaceInfo();
        log.info("start get workspace, projectId: {}, workspaceId: {}", projectId, workspaceId);

        WorkspaceMemberInfo workspaceMemberInfo = workspaceMemberService.queryWorkspaceMemberDetail(projectId,
            RequestContextUtils.getRequestUserId(), workspaceId);

        if (workspaceMemberInfo == null) {
            log.error("queryWorkspaceMemberDetail is null!");
            throw new AgentStudioException(StudioError.USER_NO_PERMISSION_DO_THIS);
        }

        WorkspaceEntity workspaceEntity = workspaceMapper.getWorkspaceByWorkspaceId(projectId, workspaceId);

        if (workspaceEntity == null) {
            return workspaceInfo;
        }

        BeanUtils.copyProperties(workspaceEntity, workspaceInfo);
        workspaceInfo.setRole(workspaceMemberInfo.getRole());

        List<ExternalMappingInfo> externalMappingInfos = workspaceMappingService.queryWorkspaceMappingInfoByWorkspaceId(
            workspaceId);
        workspaceInfo.setExternalMappingInfo(externalMappingInfos);
        return workspaceInfo;
    }

    /**
     * 验证用户上传头像
     *
     * @param icon 头像
     */
    public void validateIcon(String icon) {
        if (StringUtils.isEmpty(icon)) {
            return;
        }
        String base64Image = icon.substring(icon.indexOf(CommonConstant.SEPARATOR) + 1);
        String fileType = getFileTypeFromBase64(base64Image);
        if (StringUtils.isBlank(fileType) || !allowedIconType.contains(fileType.toLowerCase(Locale.ROOT))) {
            log.error("The file type is not supported: {}", fileType);
            throw new AgentStudioException(StudioError.WORKSPACE_ICON_FILE_TYPE_INVALID);
        }

        // 检查base64图片大小是否符合要求
        byte[] imageBytes = Base64.getDecoder().decode(base64Image);
        if (Integer.parseInt(iconMaxSize) < imageBytes.length / CommonConstant.KB) {
            throw new AgentStudioException(StudioError.WORKSPACE_ICON_EXCEED_INVALID, iconMaxSize);
        }
    }

    private String getFileTypeFromBase64(String base64String) {
        try {
            // 解码Base64字符串为字节数组
            byte[] bytes = Base64.getDecoder().decode(base64String);

            // 创建字节输入流
            ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(bytes);

            // 检测MIME类型
            String mimeType = URLConnection.guessContentTypeFromStream(byteArrayInputStream);
            String fileType = Optional.ofNullable(mimeType).map(s -> s.split("/")[1]).orElse(null);

            return "." + fileType;
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.WORKSPACE_ICON_FILE_TYPE_INVALID);
        }
    }

    @Transactional
    public void createPersonWorkspace(String projectId) {
        WorkspaceEntity workspaceEntity = new WorkspaceEntity();

        workspaceEntity.setId(UuidUtils.getUUID())
            .setName(CommonConstant.WORKSPACE.PERSON_NAME)
            .setProjectId(projectId)
            .setDescription(CommonConstant.WORKSPACE.PERSON_NAME)
            .setIcon(workSpaceDefaultIcon)
            .setFlag(null)
            .setTenantId(RequestContextUtils.getRequestUserDomainId())
            .setType(CommonConstant.WORKSPACE.TYPE.PERSON_TYPE)
            .setStatus(CommonConstant.WORKSPACE.STATUS.ENABLE)
            .setCreator(RequestContextUtils.getRequestUserName())
            .setCreatorId(RequestContextUtils.getRequestUserId())
            .setCreatedOn(new Date())
            .setUpdater(RequestContextUtils.getRequestUserName())
            .setUpdaterId(RequestContextUtils.getRequestUserId())
            .setUpdatedOn(new Date())
            .setRole(MemberRole.OWNER.getValue());

        workspaceMapper.insert(workspaceEntity);
        workspaceMemberService.addWorkspaceMember(workspaceEntity.getId(), RequestContextUtils.getRequestUserId(),
            MemberRole.OWNER.getValue());
    }

    @Override
    @DistributedLock(prefix = "workspace:create:")
    public GetWorkspaceListRsp initWorkspace(String projectId, String scope) {
        return getGetWorkspaceListRsp(projectId);
    }

    @Transactional
    public GetWorkspaceListRsp getGetWorkspaceListRsp(String projectId) {
        log.info("begin init workspace, projectId: {}, userId: {}", projectId, RequestContextUtils.getRequestUserId());
        WorkspaceEntity workspaceEntity = workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(projectId,
            RequestContextUtils.getRequestUserId());

        // 如果没有个人空间，则创建个人空间
        if (ObjectUtils.isEmpty(workspaceEntity)) {
            createPersonWorkspace(projectId);

            workspaceEntity = workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(projectId,
                RequestContextUtils.getRequestUserId());
            // 初始化个人空间时预置智能体模板到个人空间
            if (agentInitTemplateEnable) {
                createAgentTemplate(projectId, workspaceEntity.getId());
            }

        } else {
            // 兼容已经存在个人空间的教学模版预置
            if (workspaceEntity.getIsPresetAgent() == 0) {
                // 初始化个人空间时预置智能体模板到个人空间
                if (agentInitTemplateEnable) {
                    boolean isSuccess = createAgentTemplate(projectId, workspaceEntity.getId());

                    if (isSuccess) {
                        workspaceEntity.setIsPresetAgent(1);
                        workspaceMapper.updateByPrimaryKeySelective(workspaceEntity);
                    }
                }
            }
        }

        return queryWorkspace(projectId, new QueryWorkspaceQo());
    }

    public WorkspaceEntity getPersonalWorkspaceInfo(String projectId, String userId) {
        return workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(projectId, userId);
    }

    /**
     * 初始化个人空间Agent模板
     *
     * @param projectId 项目ID
     * @param workspaceId 工作区ID
     */
    public boolean createAgentTemplate(String projectId, String workspaceId) {
        try {
            ThreadLocalUtils.setWorkspaceId(workspaceId);
            // 遍历模版目录下所有JSONL文件
            List<MultipartFile> multipartFileList = getMultipartFileList(agentInitTemplatePath);

            // 逐个文件导入
            for (MultipartFile multipartFile : multipartFileList) {

                // 调用导入接口
                List<ImportListInfo> importResultList = agentManagementService.listImportFile(workspaceId, projectId,
                    multipartFile, 0, 10);

                if (importResultList == null || importResultList.isEmpty()) {
                    continue;
                }

                // 解析资源ID
                Map<String, String> resourceIds = filterResourceIds(importResultList);

                // 根据资源Type导入资源
                ImportListInfo importListInfo = importResultList.get(0);
                importResource(workspaceId, projectId, multipartFile, importListInfo.getType(), resourceIds);
            }
            return true;
        } catch (IOException e) {
            log.error("Failed to parse the agent template file: {}", e.getMessage(), e);
        } catch (AgentStudioException e) {
            log.error("Failed to import agent template, ErrorCode: {}, message: {}", e.getErrorCode(), e.getMessage(),
                e);
        } catch (Exception e) {
            log.error("Failed to init agent template: {}", e.getMessage(), e);
        }
        return false;
    }

    /**
     * 解析资源ID
     *
     * @param importResultList 导入结果列表
     * @return 资源ID映射
     */
    public Map<String, String> filterResourceIds(List<ImportListInfo> importResultList) {
        Map<String, String> resourceIds = new HashMap<>();
        resourceIds.put("agent", filterAllIdsWithDependencies(importResultList, "agent"));
        resourceIds.put("workflow", filterAllIdsWithDependencies(importResultList, "workflow"));
        resourceIds.put("plugin", filterAllIdsWithDependencies(importResultList, "Plugin"));
        resourceIds.put("controller", filterAllIdsWithDependencies(importResultList, "controller"));
        return resourceIds;
    }

    /**
     * 根据资源类型导入资源
     *
     * @param workspaceId 工作区ID
     * @param projectId 项目ID
     * @param multipartFile 多部分文件
     * @param resourceType 资源类型
     * @param resourceIds 资源ID映射
     */
    public void importResource(String workspaceId, String projectId, MultipartFile multipartFile, String resourceType,
        Map<String, String> resourceIds) {
        switch (resourceType) {
            case "agent" -> {
                agentManagementService.importAgents(workspaceId, projectId, multipartFile, resourceIds.get("agent"),
                    resourceIds.get("plugin"), resourceIds.get("workflow"), ExportModeEnum.STRICT.getCode());
            }
            case "workflow" -> {
                workflowManagementService.importWorkflows(workspaceId, projectId, multipartFile,
                    resourceIds.get("workflow"), resourceIds.get("plugin"), ExportModeEnum.STRICT.getCode());
            }
            case "controller" -> {
                agentManagementService.importAgents(workspaceId, projectId, multipartFile,
                    resourceIds.get("controller"), resourceIds.get("plugin"), resourceIds.get("workflow"), ExportModeEnum.STRICT.getCode());
            }
            default -> {
                // 无效作用域，记录错误日志并抛出异常
                log.error("createAgentTemplate: invalid source type");
            }
        }
    }

    /**
     * 递归遍历目录下所有JSON文件
     *
     * @param dir 目标目录
     * @return JSON文件列表
     */
    private List<MultipartFile> getMultipartFileList(String dir) throws IOException {
        List<MultipartFile> multipartFileList = new ArrayList<>();

        // 获取目录下所有jsonl文件
        org.springframework.core.io.Resource[] resources = resourcePatternResolver.getResources(dir);
        if (ObjectUtils.isEmpty(resources)) {
            return multipartFileList;
        }
        for (org.springframework.core.io.Resource resource : resources) {
            // 转换为MultipartFile
            MultipartFile multipartFile = new ResourceMultipartFile(resource);
            multipartFileList.add(multipartFile);
        }
        return multipartFileList;
    }

    /**
     * 筛选指定类型的资源ID
     *
     * @param importList 原始 ImportListInfo 列表
     * @param targetType 目标类型
     * @return 去重后的符合类型的 id 列表
     */
    public String filterAllIdsWithDependencies(List<ImportListInfo> importList, String targetType) {
        Set<String> idSet = new HashSet<>();

        if (importList == null || importList.isEmpty()) {
            return "";
        }

        // 递归处理所有节点
        recursiveCollectIds(importList, targetType, idSet);
        List<String> idList = new ArrayList<>(idSet);
        return String.join(",", idList);
    }

    /**
     * 递归收集所有节点（包括依赖）中符合类型的 ID
     *
     * @param nodeList 当前层级的节点列表
     * @param targetType 目标类型
     * @param idSet 存储结果的 Set
     */
    public void recursiveCollectIds(List<ImportListInfo> nodeList, String targetType, Set<String> idSet) {
        if (nodeList == null || nodeList.isEmpty()) {
            return;
        }

        for (ImportListInfo node : nodeList) {
            // 收集当前节点的 ID（如果类型匹配且 ID 不为空）
            if (targetType.equals(node.getType()) && node.getId() != null && !node.isProhibited()) {
                idSet.add(node.getId());
            }
            // 递归处理下一层依赖（因 dependencies 是 List<ImportListInfo>，直接传入递归）
            recursiveCollectIds(node.getDependencies(), targetType, idSet);
        }
    }
}

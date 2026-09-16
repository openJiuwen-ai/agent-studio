/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONWriter;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TestStatus;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateToolOpenAPIResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreateToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.GetToolVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ListToolsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ModifyToolReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyToolRsp;
import com.openjiuwen.studio.agent.common.dto.auth.PluginIAMAuthInfo;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.dto.Tool;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;
import com.openjiuwen.studio.agent.manager.dto.ToolListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.entity.Credential;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolParamLocation;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.enums.VisibilityEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.IconNameCheckUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.JsonSchemaUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.swagger.v3.core.util.Json;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.Paths;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.parameters.RequestBody;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.responses.ApiResponses;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * 工具管理服务
 *
 */
@Slf4j
@Service
public class ToolManagementService implements IToolManagementService {
    /**
     * 接口测试OBS过期时间
     */
    private static final int TOOL_TEST_OBS_EXPIRES = 1;

    /**
     * 接口测试OBS临时目录
     */
    private static final String TOOL_TEST_OBS_PATH = "temp/tools/openapi";

    /**
     * 预置插件前缀
     */
    private static final String PRESET = "preset_";

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${tool.jsonschema.max-prop-num}")
    private int maxPropNum;

    @Value("${tool.jsonschema.max-prop-depth}")
    private int maxPropDepth;

    @Value("${tool.name.black-list}")
    private String toolNameBlackList;

    @Value("${tool.default-icon}")
    private String defaultIcon;

    @Value("${inner.exclude-tools}")
    private String excludeInnerTools;

    @Value("${tool.max-release-version-size}")
    private int releaseMaxSize;

    @Value("${op.svc.preset-plugin:opsvc_project_mock}")
    private String presetPlugin;

    @Value("${spring.is-soft-delete: true}")
    private Boolean isSoftDelete;

    @Autowired
    private IPluginBase pluginBase;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    private final MgObsService obsService;

    private final ReleaseVersionMapper releaseVersionMapper;

    private final ToolMapper toolMapper;

    private final ToolCredentialMapper toolCredentialMapper;

    private final MappingMapper mappingMapper;

    private final UrlCheckUtils urlCheckUtils;

    private final AgentCommonService agentCommonService;

    private final MessageSource messageSource;

    private final AgentMapper agentMapper;

    private final WorkflowMapper workflowMapper;

    private final I18nUtil i18nUtil;

    private final PluginMapper pluginMapper;

    private final AgentServiceProxyService agentServiceProxyService;

    public ToolManagementService(ToolMapper toolMapper, MappingMapper mappingMapper, UrlCheckUtils urlCheckUtils,
                                 MgObsService obsService, ReleaseVersionMapper releaseVersionMapper, AgentCommonService agentCommonService,
                                 ToolCredentialMapper toolCredentialMapper, MessageSource messageSource, AgentMapper agentMapper, WorkflowMapper workflowMapper,
                                 I18nUtil i18nUtil, PluginMapper pluginMapper, AgentServiceProxyService agentServiceProxyService) {
        this.toolMapper = toolMapper;
        this.mappingMapper = mappingMapper;
        this.urlCheckUtils = urlCheckUtils;
        this.obsService = obsService;
        this.releaseVersionMapper = releaseVersionMapper;
        this.agentCommonService = agentCommonService;
        this.toolCredentialMapper = toolCredentialMapper;
        this.messageSource = messageSource;
        this.agentMapper = agentMapper;
        this.workflowMapper = workflowMapper;
        this.i18nUtil = i18nUtil;
        this.pluginMapper = pluginMapper;
        this.agentServiceProxyService = agentServiceProxyService;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Tool",
        description = "创建工具",
        resourceId = "-1",
        resourceName = "body.toolDisplayName"
    )
    public CreateToolRsp createToolV1(String projectId, String workspaceId, CreateToolReq body) {
        ToolEntity toolEntity = buildToolEntity(projectId, workspaceId, body, false);
        int existDisplayName = toolMapper.selectByDisplayNameAndWorkspaceId(toolEntity.getToolDisplayName(), toolEntity.getWorkspaceId());
        if(existDisplayName > 0) {
            throw new AgentStudioException(StudioError.TOOL_EN_NAME_ALREADY_EXIST);
        }
        try {
            toolMapper.insert(toolEntity);
        } catch (DuplicateKeyException e) {
            log.error("Fail to create tool for duplicate tool name [{}] under tenant [{}]", body.getToolDisplayName(),
                    projectId);
            throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
        }

        return new CreateToolRsp().setToolId(toolEntity.getToolId());
    }

    @Override
    @OperationLog(
        operationType = OperationType.READ,
        resourceType = "Tool",
        description = "查询工具是否被使用",
        resourceId = "toolId",
        resourceName = ""
    )
    public Boolean checkToolIsUsed(String projectId, String workspaceId, String toolId) {
        int agentCount = this.agentMapper.selectByAgentIdAndResourceId(projectId, workspaceId, toolId, "tool");
        if (agentCount > 0) {
            return true;
        }
        int workflowCount = this.workflowMapper.selectByWorkflowIdAndResourceId(projectId, workspaceId, toolId, "tool");
        return workflowCount > 0;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Tool",
        description = "创建工具OpenAPI",
        resourceId = "-1",
        resourceName = "body.toolDisplayName"
    )
    public CreateToolOpenAPIResponseBody createToolOpenAPI(String projectId, String workspaceId, CreateToolReq body) {
        ToolEntity toolEntity = buildToolEntity(projectId, workspaceId, body, true);

        // 根据toolEntity对象转化为OpenAPI定义并上传到obs
        uploadToolOpenAPI(toolEntity);
        return new CreateToolOpenAPIResponseBody().setToolId(toolEntity.getToolId());
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Tool",
        description = "创建工具OpenAPI",
        resourceId = "toolId",
        resourceName = ""
    )
    public CreateToolOpenAPIResponseBody createToolOpenAPIByIdV1(String projectId, String toolId, String workspaceId) {
        // 插件详情页插件调测功能，插件信息从数据库表里取
        ToolEntity toolEntity = pluginBase.buildToolByPlugin(projectId, workspaceId, toolId, "0");
        if (toolEntity == null) {
            log.error("tool:{} not exist and can not create the tool OpenAPI.", toolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }

        // 根据toolEntity对象转化为OpenAPI定义并上传到obs
        uploadToolOpenAPI(toolEntity);
        return new CreateToolOpenAPIResponseBody().setToolId(toolId);
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Tool",
        description = "删除工具",
        resourceId = "toolId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteToolV1(String projectId, String toolId, String workspaceId) {
        ToolEntity toolEntity = toolMapper.selectByPrimaryKeyAndWorkspace(toolId, projectId, workspaceId);
        if (Objects.isNull(toolEntity)) {
            return null;
        }

        // 设置关联的资源为已失效
        mappingMapper.updateValidByResourceIdAndVersionId(toolId, null);
        // 删除已发布的版本
        releaseVersionMapper.deleteByAppId(toolId);
        if (isSoftDelete) {
            // 软删除插件
            toolMapper.copyToHistoryTool(toolId, projectId, UUID.randomUUID().toString());
        } else {
            // 删除OBS资源
            List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(toolId);
            releaseVersions.forEach(releaseVersion -> obsService.deleteObsFile(releaseVersion.getDslPath()));
        }
        // 真正执行删除操作
        toolMapper.deleteByPrimaryKey(toolId, projectId);


        log.info("delete tool version toolId = {}", toolId);
        return new CommonDeleteRsp().setId(toolId);
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Tool",
        description = "删除工具版本",
        resourceId = "toolId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteToolVersion(String projectId, String versionId, String toolId, String workspaceId) {
        ToolEntity toolEntity = toolMapper.selectByPrimaryKeyAndWorkspace(toolId, projectId, workspaceId);
        if (Objects.isNull(toolEntity)) {
            return null;
        }

        // 自定义工具，需要校验用户id
        if (!isOpTenant(projectId)
                && !Objects.equals(toolEntity.getCreatorId(), RequestContextUtils.getRequestUserId())) {
            throw new AgentStudioException(StudioError.NO_PERMISSION_DELETE_TOOL);
        }

        // 校验该版本是否被共享
        shareInnerService.cancelPluginVersionShared(projectId, workspaceId, toolId, versionId);

        // 删除OBS资源
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(toolId, versionId);
        obsService.deleteObsFile(releaseVersion.getDslPath());
        // 设置关联的资源为已失效
        mappingMapper.updateValidByResourceIdAndVersionId(toolId, versionId);
        // 删除已发布的版本
        releaseVersionMapper.deleteByAppIdAndVersionId(toolId, versionId);

        // 更新last_version_id
        List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(toolId);
        if (releaseVersions == null || releaseVersions.isEmpty()) {
            // 更新发布状态
            toolMapper.updatePublished(toolId,projectId, 0);
        }
        Optional<String> latestVersion = releaseVersions.stream()
                .map(ReleaseVersion::getVersionId)
                .max(Comparator.naturalOrder());
        toolMapper.updateLastVersionId(toolId, projectId, latestVersion.orElse(null));

        log.info("delete tool version toolId = {}, toolVersion={}", toolId, versionId);
        return new CommonDeleteRsp().setId(toolId).setVersionId(versionId);
    }

    @Override
    public ToolListRsp listToolsV1(String projectId, ListToolsV1Qo listToolsQo) {
        List<ToolEntity> toolEntityList =
                getToolEntityList(projectId, listToolsQo.getWorkspaceId(), convertSearchCriteriaFromListToolsQo(listToolsQo));

        List<Tool> tools = new ArrayList<>();
        toolEntityList.forEach(toolEntity -> {
            if (toolEntity == null) {
                throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, "can not find any tools");
            }
            Tool tool = convertToolFromToolEntity(toolEntity);
            if (CommonConstant.USER.equals(tool.getVisibility()) && !tool.getCreatorId().equals(RequestContextUtils.getRequestUserId())) {
                return;
            }
            tools.add(tool);
        });

        ToolListRsp toolListRsp = new ToolListRsp();

        // 根据语言处理返回结果
        Locale locale = LanguageUtils.getLanguageLocale();
        tools.forEach(tool -> {
            if (CommonConstant.DEFAULT_USERNAME.equals(tool.getCreator())) {
                tool.setCreator(messageSource.getMessage("tool.creator.official", null,
                        CommonConstant.DEFAULT_USERNAME, locale));
            }
        });

        toolListRsp.setToolList(tools.subList(listToolsQo.getOffset(), Math.min(listToolsQo.getLimit() + listToolsQo.getOffset(), tools.size())));
        toolListRsp.setCount((long) tools.size());
        return toolListRsp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Tool",
        description = "修改工具",
        resourceId = "toolId",
        resourceName = "body.toolDisplayName"
    )
    public ModifyToolRsp modifyToolV1(String projectId, String workspaceId, String toolId, ModifyToolReq body) {
        List<ToolEntity> toolEntities = toolMapper.selectByWorkspaceIdAndProjectId(projectId, workspaceId, toolId);
        toolEntities.forEach(toolEntity -> {
            String toolDisplayName = toolEntity.getToolDisplayName();
            if (Strings.CS.equals(toolDisplayName, body.getToolDisplayName())) {
                throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
            }
        });
        // 工具参数信息校验
        checkUrl(body.getRequestInfo(), projectId);
        checkToolInfo(body.getToolDisplayName(), body.getInputSchema(), body.getOutputSchema(), null,
                body.getIntfType());
        ToolEntity oldTool = toolMapper.selectByPrimaryKeyAndWorkspace(toolId, projectId, workspaceId);
        if (Objects.isNull(oldTool)) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, String.format("tool id %s not exist", toolId));
        }

        // 预置插件支持修改auth描述
        if (ToolType.INNER.type.equals(oldTool.getType()) && Boolean.TRUE.equals(oldTool.getAuthRequired())) {
            clearAuthInfo(body.getAuthInfo());
        } else {
            body.setAuthInfo(encryptedAuthInfo(body.getAuthInfo()));
        }

        ToolEntity newTool = ConvertToolFromModifyBody(body);
        // 发布为自定义节点校验
        Integer customizeNode = newTool.getCustomizeNode();
        if (customizeNode != null && !customizeNode.equals(oldTool.getCustomizeNode())) {
            agentCommonService.publishCustomizeNodeCheck(projectId, toolId, oldTool.getLastVersionId(), customizeNode);
        }

        String icon;
        if (body.getIcon() == null) {
            icon = oldTool.getIcon();
        } else {
            IconNameCheckUtils.validaIconName(body.getIcon());
            newTool.setIconName(body.getIcon());
            icon = ImageBase64Utils.getImageBase64(body.getIcon(), obsService);
        }
        newTool.setIcon(icon);

        // 入参支持为空，删除所有入参时，inputSchema为null，此时要设置为空串，主动更新数据库
        newTool.setInputSchema(Optional.ofNullable(body.getInputSchema()).orElse(""));
        newTool.setToolId(toolId);
        newTool.setProjectId(projectId);

        if (StringUtils.isEmpty(body.getTestStatus())) {
            // 除设置业务节点，插件测试状态置为未知
            if (customizeNode == null) {
                newTool.setTestStatus(TestStatus.UNKNOWN.getCode());
            }
        } else {
            newTool.setTestStatus(TestStatus.valueOf(body.getTestStatus()).getCode());
        }

        try {
            toolMapper.updateByPrimaryKeySelective(newTool);
        } catch (DuplicateKeyException exception) {
            log.error("Fail to modify tool for duplicate tool name [{}] under tenant [{}]", body.getToolDisplayName(),
                    projectId);
            throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
        }
        return new ModifyToolRsp().setToolId(toolId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Tool",
        description = "发布工具版本",
        resourceId = "toolId",
        resourceName = ""
    )
    public VersionInfo releaseToolVersion(String projectId, String toolId, String workspaceId, CreateVersionReq body) {
        // 检查是否测试成功
        ToolEntity toolEntity = toolMapper.selectByPrimaryKeyAndWorkspace(toolId, projectId, workspaceId);
        // 校验用户id
        String requestUserId = RequestContextUtils.getRequestUserId();
        if (!isOpTenant(projectId) && !Strings.CS.equals(toolEntity.getCreatorId(), requestUserId)) {
            log.error("{} try to publish a tool create by {}", requestUserId, toolEntity.getCreatorId());
            throw new AgentStudioException(StudioError.NO_CREATOR_PERMISSION);
        }

        // 校验发布版本数量
        List<ReleaseVersion> releaseVersionList = releaseVersionMapper.selectByAppId(toolId);
        if (releaseVersionList.size() > releaseMaxSize) {
            log.error("release version reach the max size {}", releaseVersionList.size());
            throw new AgentStudioException(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT);
        }

        // 发布版本
        ReleaseVersion releaseVersion =
                releaseToolVersionHandler(toolEntity, null, body.getVersionName(), body.getVersionNote());

        // 更新最新版本号
        ToolEntity newToolEntity = new ToolEntity();
        newToolEntity.setToolId(toolEntity.getToolId());
        newToolEntity.setProjectId(toolEntity.getProjectId());
        newToolEntity.setLastVersionId(releaseVersion.getVersionId());
        newToolEntity.setPublished(1);
        toolMapper.updateByPrimaryKeySelective(newToolEntity);

        log.info("release a new tool version {}", releaseVersion);
        return releaseVersion.convertToInfo();
    }

    @Override
    public Tool getToolVersion(String projectId, String versionId, String toolId, GetToolVersionQo getToolVersionQo) {
        ToolEntity toolEntity = pluginBase.getToolEntityByVersion(toolId, versionId);
        if (!Strings.CS.equals(toolEntity.getType(), ToolType.INNER.type) && !Strings.CS.equals(
                toolEntity.getWorkspaceId(), getToolVersionQo.getWorkspaceId())) {
            // 判断是否共享资源
            ShareScopeEntity shareScopeEntity = shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(toolId,
                ThreadLocalUtils.getWorkspaceId());
            // 非空表示跨空间引用查询，检查版本号是否被共享
            if (ObjectUtils.isNotEmpty(shareScopeEntity)) {
                // 检查工作流是否被授权
                ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(
                    toolId);
                if (!shareResourceEntity.containsVersion(versionId)) {
                    log.error(
                        "getToolVersion, request project id: {} workspace id: {}, tool project id {} workspace id {}",
                        projectId, getToolVersionQo.getWorkspaceId(), toolEntity.getProjectId(),
                        toolEntity.getWorkspaceId());
                    throw new AgentStudioException(StudioError.PLUGIN_PRIVILEGE_ERROR, toolEntity.getProjectId());
                }
            }else {
                log.error("getToolVersion, request project id: {} workspace id: {}, tool project id {} workspace id {}",
                    projectId, getToolVersionQo.getWorkspaceId(), toolEntity.getProjectId(), toolEntity.getWorkspaceId());
                throw new AgentStudioException(StudioError.PLUGIN_PRIVILEGE_ERROR, toolEntity.getProjectId());
            }
        }

        return convertToolFromToolEntity(toolEntity);
    }

    @Override
    public VersionListRsp listToolVersions(String projectId, String toolId, String workspaceId) {
        checkToolPermission(projectId, workspaceId, toolId);
        return agentCommonService.listVersions(toolId, releaseMaxSize);
    }

    public void checkToolPermission(String projectId, String workspaceId, String toolId) {
        ToolEntity toolEntity = toolMapper.selectByPrimaryKeyAndWorkspace(toolId, projectId, workspaceId);
        if (Objects.isNull(toolEntity)) {
            log.error("Tool {} projectId {} workspaceId {} does not exist.", toolId, projectId, workspaceId);
            throw new AgentStudioException(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, toolId, projectId, workspaceId);
        }
    }

    @Override
    public Tool retrieveToolV1(String projectId, String toolId, String workspaceId) {
        ToolEntity toolEntity =
                toolMapper.selectByPrimaryKeyAndWorkspace(toolId, null, null);
        if (toolEntity == null) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, String.format("tool id %s not exist", toolId));
        }
        if (!Strings.CS.equals("inner", toolEntity.getType()) && !Strings.CS.equals(toolEntity.getProjectId(), projectId) && !Strings.CS.equals(toolEntity.getWorkspaceId(), workspaceId)) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, String.format("tool id %s not exist", toolId));
        }
        return convertToolFromToolEntity(toolEntity);
    }

    /**
     * 预置插件支持增加鉴权凭证
     */
    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Tool",
        description = "增加工具凭证",
        resourceId = "toolId",
        resourceName = ""
    )
    public ToolCredential addToolCredential(String projectId, String toolId, String workspaceId, Boolean needValidate,ToolCredential body ) {
        log.info("operation log {}: start to add plugin credential", projectId);
        if (needValidate == null) {
            needValidate = false;
        }
        checkInnerToolPermission(toolId);
        ToolCredential oldtoolCredential =
                toolCredentialMapper.selectByToolId(projectId, toolId, workspaceId);
        if(oldtoolCredential != null) {
            throw new AgentStudioException(StudioError.TOOL_CREDENTIAL_ALREADY_EXIST);
        }
        checkToolCredential(projectId, toolId, body);
        encryptAuthKeyInfo(body.getAuthKeys());
        if(needValidate){
            validateToolCredential(projectId,workspaceId,toolId,body);
        }
        ToolCredential toolCredential = new ToolCredential();
        toolCredential.setId(UUID.randomUUID().toString());
        toolCredential.setToolId(toolId);
        toolCredential.setProjectId(projectId);
        toolCredential.setCreatorId(RequestContextUtils.getRequestUserId());
        toolCredential.setAuthKeys(body.getAuthKeys());
        toolCredential.setWorkspaceId(workspaceId);
        toolCredential.setDomainId(RequestContextUtils.getRequestUserDomainId());
        try {
            toolCredentialMapper.insert(toolCredential);
        } catch (DuplicateKeyException e) {
            log.error("Fail to add preset tool credential for duplicate reason");
            throw new AgentStudioException(StudioError.TOOL_CREDENTIAL_ALREADY_EXIST);
        }

        // 上传OBS
        uploadCredentialsIr(toolCredential, toolId);

        // 隐藏key值
        List<AuthKeyInfo> authKeys = toolCredential.getAuthKeys();
        for (AuthKeyInfo authkey : authKeys) {
            authkey.setAuthKey(null);
        }

        return toolCredential;
    }

    private SearchCriteria convertSearchCriteriaFromListToolsQo(ListToolsV1Qo listToolsQo) {
        return new SearchCriteria().setId(listToolsQo.getId())
                .setIds(listToolsQo.getIds())
                .setName(StrUtils.filterSpecialWords(listToolsQo.getEnName()))
                .setToolChineseName(StrUtils.filterSpecialWords(listToolsQo.getCnName()))
                .setToolDesc(StrUtils.filterSpecialWords(listToolsQo.getDesc()))
                .setType(listToolsQo.getType())
                .setIntfType(listToolsQo.getIntfType())
                .setCreator(listToolsQo.getCreator())
                .setUserId(listToolsQo.getCreatorId())
                .setPublished(listToolsQo.isPublished())
                .setCustomizeNode(listToolsQo.isCustomizeNode());
    }

    /**
     * 检查凭证信息，是否为预置插件，是否有authkey，插件是否存在
     */
    private void checkToolCredential(String projectId, String toolId, ToolCredential credential) {
        if (credential.getAuthKeys() == null) {
            throw new AgentStudioException(StudioError.TOOL_AUTHENTICATION_FAILED);
        }
        PluginEntity info = pluginMapper.selectPluginEntityWithCredential(toolId, opSvcProjectId, RequestContextUtils.getRequestUserId());
        if (info == null) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        if (!info.getType().equals(ToolType.INNER.type)) {
            throw new AgentStudioException(StudioError.TOOL_AUTHENTICATION_FAILED);
        }
        if(!isOpTenant(projectId)&& !info.getAuthRequired()){
            throw new AgentStudioException(StudioError.TOOL_AUTHENTICATION_FAILED);
        }

    }

    private void validateToolCredential(String projectId, String workspaceId, String pluginId, ToolCredential credential) {
        // 用第一个工具进行鉴权信息的验证，不携带任何参数，避免请求成功消耗资源使用次数
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, null, null);
        String toolId = "0";
        if (StringUtils.isNotBlank(pluginEntity.getInputSchema()) && pluginEntity.getInputSchema()
                .contains("tool_id")) {
            List<ToolInputSchema> ToolInputSchemas = JSON.parseArray(pluginEntity.getTestStatus(), ToolInputSchema.class);
            toolId = ToolInputSchemas.get(0).getToolId();
        }
        // 获取插件的toolEntity对象(调测使用老版本tool对象)
        ToolEntity newTool = pluginBase.buildToolByPlugin(projectId, workspaceId, pluginId, toolId);
        // 替换内置鉴权信息为用户设置的鉴权信息
        newTool.getAuthInfo().setAuthKeys(credential.getAuthKeys());
        // 默认使用了toolId作为obs中的key,多用户同时使用会冲突，替换为唯一key
        String obsKey = UUID.randomUUID().toString();
        newTool.setToolId(obsKey);
        // 根据toolEntity对象转化为OpenAPI定义并上传到obs
        uploadToolOpenAPI(newTool);
        // 执行调测
        RunToolRequestBody requestBody = new RunToolRequestBody().setToolObsKey(obsKey).setParameter("{}");
        String workspace_id = RequestContextUtils.getRequestWorkspaceId();
        String project_id = RequestContextUtils.getRequestProjectId();
        ResponseEntity<RunToolResponseBody> runToolResponseBodyResponseEntity = agentServiceProxyService.runToolForValidateToolCredential(workspace_id, project_id, requestBody, obsKey);
        RunToolResponseBody responseBody = runToolResponseBodyResponseEntity.getBody();
        // 如果是401鉴权失败则抛出异常，不设置鉴权
        if (responseBody != null && responseBody.getRawResponseCode() == 401) {
            String errorMessage = responseBody.getRawResponse();
            throw new AgentStudioException(StudioError.PLUGIN_AUTH_DATA_INVALID,Collections.singletonList(errorMessage));
        }
    }

    /**
     * 加密鉴权信息
     *
     * @param authKeyInfos
     */
    private void encryptAuthKeyInfo(List<AuthKeyInfo> authKeyInfos) {
        if (authKeyInfos != null) {
            authKeyInfos.forEach(item -> {
                if (StringUtils.isNotBlank(item.getAuthKey())) {
                    item.setAuthKey(encryptionAdapter.encrypt(item.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
                }
            });
        }
    }

    /**
     * 上传预置插件的凭证至OBS credential/ir/{user_id}/{tool_id}.json
     */
    private void uploadCredentialsIr(ToolCredential toolCredential, String toolId) {
        // 获取预置插件
        PluginEntity toolEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(toolId, null, null);
        if (toolEntity == null) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, "tool not exist");
        }
        AuthInfo authInfo = toolEntity.getAuthInfo();
        // 更新认证信息的认证密钥
        authInfo.setAuthKeys(toolCredential.getAuthKeys());
        Credential irCredential = new Credential();
        irCredential.setName(toolEntity.getPluginChineseName());
        irCredential.setScope(authInfo.getScope());
        irCredential.setDomain(authInfo.getDomain());

        List<Credential.AuthKey> credentialAuthKeys = authInfo.getAuthKeys().stream().map(authKeyInfo -> {
            Credential.AuthKey key = new Credential.AuthKey();
            key.setAuthName(authKeyInfo.getTargetName());
            key.setAuthValue(authKeyInfo.getAuthKey());
            return key;
        }).collect(Collectors.toList());
        irCredential.setAuthKeys(credentialAuthKeys);
        String irPath = obsService.uploadObsFile(String.format("%s/%s/%s.json", CommonConstant.CREDENTIAL_IR,
                        RequestContextUtils.getRequestUserId(), toolId),
                JSON.toJSONString(irCredential, JSONWriter.Feature.WriteMapNullValue), -1);
        log.info("preset tool credential obs file uploaded: {}", irPath);
    }

    public String uploadToolOpenAPI(ToolEntity toolEntity) {
        // 转换为openapi定义
        String openapiJson = transferToolOpenApi(toolEntity);

        // 上传OBS
        String path = String.format("%s/%s.json", TOOL_TEST_OBS_PATH, toolEntity.getToolId());
        String uploadedObsFile = obsService.uploadObsFile(path, openapiJson, TOOL_TEST_OBS_EXPIRES);
        log.info("open api obs file uploaded: {}", uploadedObsFile);
        return path;
    }

    private List<AuthKeyInfo> updateAuthKeys(List<AuthKeyInfo> updates, List<AuthKeyInfo> existingKeys) {
        // 创建更新映射表
        Map<String, String> updateMap = new HashMap<>();
        for (AuthKeyInfo update : updates) {
            if (update.getTargetName() != null && update.getAuthKey() != null) {
                updateMap.put(update.getTargetName(), update.getAuthKey());
            }
        }

        // 更新现有密钥
        for (AuthKeyInfo existing : existingKeys) {
            String newKey = updateMap.get(existing.getTargetName());
            if (newKey != null) {
                existing.setAuthKey(encryptionAdapter.encrypt(newKey, RequestContextUtils.getRequestUserDomainId()));
            }
        }

        return existingKeys;
    }

    /**
     * 预置插件删除鉴权凭证
     */
    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Tool",
        description = "删除工具凭证",
        resourceId = "toolId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteToolCredential(String projectId, String toolId, String workspaceId) {
        log.info("operation log {}: start to delete plugin credential", projectId);
        checkInnerToolPermission(toolId);
        ToolCredential toolCredential =
                toolCredentialMapper.selectByToolId(projectId, toolId, workspaceId);
        if (toolCredential == null) {
            throw new AgentStudioException(StudioError.TOOL_CREDENTIAL_NOT_EXIST);
        }
        toolCredentialMapper.deleteByToolId(projectId, RequestContextUtils.getRequestUserId(), toolId, workspaceId);
        // 删除credential ir文件
        obsService.deleteObsFile(String.format("%s/%s/%s.json", CommonConstant.CREDENTIAL_IR,
                RequestContextUtils.getRequestUserId(), toolId));
        log.info("delete tool credential succeeded, delete tool credential");
        return new CommonDeleteRsp().setId(toolId);
    }

    @NotNull
    public ToolEntity buildToolEntity(String projectId, String workspaceId, CreateToolReq body, boolean isCreateOpenAPI) {
        // 工具参数信息校验
        checkUrl(body.getRequestInfo(), projectId);
        checkToolInfo(body.getToolDisplayName(), body.getInputSchema(), body.getOutputSchema(), body.getVisibility(),
                body.getIntfType());

        // op账号创建并且auth_required信息为true的，清空AuthInfo信息
        if (isOpTenant(projectId) && body.isAuthRequired()) {
            clearAuthInfo(body.getAuthInfo());
        } else if (isCreateOpenAPI) { // 插件调试时页面数据为脱敏数据，不可用，需取数据库配置
            PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(body.getPluginId(), null, null);
            body.setAuthInfo(pluginEntity.getAuthInfo());
        } else {
            body.setAuthInfo(encryptedAuthInfo(body.getAuthInfo()));
        }

        // 普通租户创建工具类型是自定义，承载租户创建工具类型是预置，知识库工具标识在metadata中
        ToolEntity toolEntity = new ToolEntity();

        // 如果为OP账号创建的内置插件，插件id固定，使用前缀+小写英文名；否则使用UUID
        if (body.getPluginId() != null && StringUtils.isNotEmpty(body.getPluginId())) {
            toolEntity.setToolId(body.getPluginId());
        } else {
            toolEntity.setToolId(isOpTenant(projectId) ? PRESET + StringUtils.lowerCase(body.getToolDisplayName()) :
                UUID.randomUUID().toString());
        }
        toolEntity.setTraceId(toolEntity.getToolId());
        toolEntity.setProjectId(projectId);
        toolEntity.setWorkspaceId(workspaceId);
        toolEntity.setToolDisplayName(body.getToolDisplayName());
        toolEntity.setToolChineseName(body.getToolChineseName());
        toolEntity.setToolDesc(body.getToolDesc());
        if (body.getIcon() == null) {
            toolEntity.setIcon(defaultIcon);
        } else {
            IconNameCheckUtils.validaIconName(body.getIcon());
            toolEntity.setIconName(body.getIcon());
            String icon = ImageBase64Utils.getImageBase64(body.getIcon(), obsService);
            toolEntity.setIcon(icon);
        }
        toolEntity.setRequestInfo(body.getRequestInfo());
        if (!Objects.isNull(body.getAuthInfo()) && AuthInfo.ScopeEnum.IAM.equals(body.getAuthInfo().getScope())
                && !Objects.isNull(body.getAuthInfo().getIamCredentials())) {
            body.getAuthInfo()
                    .getIamCredentials()
                    .put(CommonConstant.DOMAIN_ID, RequestContextUtils.getRequestUserDomainId());
        }

        toolEntity.setAuthInfo(body.getAuthInfo());
        toolEntity.setIntfType(
                StringUtils.isEmpty(body.getIntfType()) ? CommonConstant.Plugin.INTF_TYPE_BLOCKING : body.getIntfType());
        toolEntity.setVisibility(body.getVisibility());
        toolEntity.setInputSchema(body.getInputSchema());
        toolEntity.setOutputSchema(body.getOutputSchema());
        toolEntity.setIsInputList(body.isIsInputList());
        toolEntity.setIsOutputList(body.isIsOutputList());
        toolEntity.setType(toolEntity.getType() != null ? toolEntity.getType() : getToolType(projectId));
        toolEntity.setMetadata(body.getMetadata());

        toolEntity.setCreator(
                isOpTenant(projectId) ? CommonConstant.DEFAULT_USERNAME : RequestContextUtils.getRequestUserName());
        toolEntity.setCreatorId(RequestContextUtils.getRequestUserId());

        toolEntity.getRequestInfo()
                .setHeaders(Optional.ofNullable(toolEntity.getRequestInfo().getHeaders()).orElse(new HashMap<>()));
        toolEntity.setAuthRequired(body.isAuthRequired());
        return toolEntity;
    }

    /**
     * 发布插件对象
     *
     * @param toolEntity tool对象
     * @param versionId versionId
     * @param versionName 版本名称
     * @param versionNote 版本备注
     * @return 发布版本对象
     */
    public ReleaseVersion releaseToolVersionHandler(ToolEntity toolEntity, String versionId, String versionName,
                                                    String versionNote) {
        String toolId = toolEntity.getToolId();
        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion
                .setVersionId(StringUtils.isBlank(versionId) ? String.valueOf(System.currentTimeMillis()) : versionId);

        // 发布到OBS
        toolEntity.setLastVersionId(null);
        String releaseDslPath =
                obsService.uploadObsFile(toolId, toolId + Constants.UNDERLINE_STR + releaseVersion.getVersionId(),
                        CommonConstant.TOOL, JsonUtils.toJson(toolEntity), CommonConstant.DSL_STR);
        releaseVersion.setDslPath(releaseDslPath);

        // 新版本insert t_release_version
        toolEntity.setPublished(1);
        toolMapper.updateByPrimaryKeySelective(toolEntity);
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setReleasedOn(new Date());

        releaseVersion.setVersionName(versionName);
        releaseVersion.setVersionNote(versionNote);

        releaseVersion.setAppType(CommonConstant.TOOL_TYPE);
        releaseVersion.setStatus(CommonConstant.NORMAL);

        releaseVersion.setAppId(toolEntity.getToolId());

        releaseVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersion.setCreatorId(RequestContextUtils.getRequestUserId());

        releaseVersionMapper.insert(releaseVersion);
        return releaseVersion;
    }

    private ToolEntity ConvertToolFromModifyBody(ModifyToolReq body) {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolDisplayName(body.getToolDisplayName());
        toolEntity.setToolChineseName(body.getToolChineseName());
        toolEntity.setToolDesc(body.getToolDesc());
        toolEntity.setIntfType(body.getIntfType());
        toolEntity.setRequestInfo(body.getRequestInfo());
        toolEntity.setAuthInfo(body.getAuthInfo());
        toolEntity.setInputSchema(body.getInputSchema());
        toolEntity.setIsInputList(body.isIsInputList());
        toolEntity.setOutputSchema(body.getOutputSchema());
        toolEntity.setIsOutputList(body.isIsOutputList());
        toolEntity.setMetadata(body.getMetadata());

        if (body.isCustomizeNode() != null) {
            toolEntity.setCustomizeNode(body.isCustomizeNode() ? 1 : 0);
        }
        return toolEntity;
    }

    public void checkUrl(RequestInfo requestInfo, String projectId) {
        if (requestInfo == null || StringUtils.isEmpty(requestInfo.getUrl())) {
            return;
        }
        if (requestInfo.getUrl().contains("{")) {
            // 有占位符的url，不具备checkUrl条件，先跳过
            return;
        }
        urlCheckUtils.checkUrl(projectId, requestInfo.getUrl());
    }

    /**
     * 清空鉴权信息
     *
     * @param authInfo
     */
    private void clearAuthInfo(AuthInfo authInfo) {
        if (authInfo == null || authInfo.getAuthKeys() == null) {
            return;
        }
        authInfo.getAuthKeys().forEach(item -> {
            item.setAuthKey("");
        });
    }

    public String transferToolOpenApi(ToolEntity toolEntity) {
        log.info("generate new open api file for {}", toolEntity.getToolId());

        // 生成参数列表
        List<Parameter> parameters = new ArrayList<>();

        SchemaConfig requestBody = SchemaConfig.builder()
                .location(ToolParamLocation.BODY.location)
                .required(new ArrayList<>())
                .properties(new HashMap<>())
                .build();

        parseInputSchema(toolEntity.getInputSchema(), parameters, requestBody);
        parseInputSchema(toolEntity.getRequestInfo().getInputSchema(), parameters, requestBody);

        String contentType = toolEntity.getRequestInfo().getHeaders().get(CommonConstant.CONTENT_TYPE);
        if (contentType == null || contentType.isEmpty() || !CommonConstant.MULTIPART_FORM_DATA.equals(contentType)) {
            contentType = CommonConstant.APPLICATION_JSON;
        }

        // 创建content对象
        Content content = null;
        if (CommonConstant.Plugin.INTF_TYPE_BLOCKING.equals(toolEntity.getIntfType())) {
            // 非流式
            content = new Content().addMediaType(contentType,
                    new MediaType().schema(JsonUtils.json2ObjQuietly(toolEntity.getOutputSchema(), Schema.class)));
        } else if (CommonConstant.Plugin.INTF_TYPE_STREAMING.equals(toolEntity.getIntfType())) {
            // 流式
            content = new Content().addMediaType(CommonConstant.TEXT_EVENT_STREAM,
                    new MediaType().schema(new StringSchema()));
        }

        // 创建Operation对象
        Operation operation =
            new Operation().operationId(toolEntity.getToolId())
                .summary(toolEntity.getToolDisplayName())
                .description(toolEntity.getToolDesc())
                // server的url为完整的url，path设置为"/"
                .servers(List.of(new Server().url(toolEntity.getRequestInfo().getUrl())))
                .parameters(parameters)
                .requestBody(
                    new RequestBody()
                        .content(new Content().addMediaType(contentType, new MediaType()
                            .schema(JsonUtils.json2ObjQuietly(JsonUtils.toJson(requestBody), Schema.class))))
                        .extensions(Map.of(CommonConstant.OpenAPI.X_ARRAY_ENCAPSULATION, toolEntity.getIsInputList())))
                .responses(new ApiResponses().addApiResponse("200",
                    new ApiResponse().description(toolEntity.getToolDesc())
                        .content(content)
                        .extensions(Map.of(CommonConstant.OpenAPI.X_ARRAY_ENCAPSULATION, toolEntity.getIsOutputList()))));

        // 设置Method
        PathItem pathItem = switch (toolEntity.getRequestInfo().getMethod()) {
            case GET -> new PathItem().get(operation);
            case POST -> new PathItem().post(operation);
        };

        // 创建OpenAPI对象
        OpenAPI openAPI = new OpenAPI().info(
                new Info().title(toolEntity.getToolDisplayName()).version(String.valueOf(System.currentTimeMillis())));
        openAPI = openAPI.paths(new Paths().addPathItem("/", pathItem));

        // 设置鉴权信息
        AuthInfo authInfo = toolEntity.getAuthInfo();
        if (authInfo != null && !CollectionUtils.isEmpty(authInfo.getAuthKeys())) {
            if (authInfo.getScope() == AuthInfo.ScopeEnum.SERVICE) {
                SecurityScheme securityScheme = new SecurityScheme();
                switch (authInfo.getDomain()) {
                    case QUERY -> securityScheme.in(SecurityScheme.In.QUERY);
                    case HEADERS -> securityScheme.in(SecurityScheme.In.HEADER);
                }
                AuthKeyInfo authKeyInfo = authInfo.getAuthKeys().get(0);
                securityScheme.setName(authKeyInfo.getTargetName());
                securityScheme.setType(SecurityScheme.Type.APIKEY);
                // 加密后的值存储在自定义字段
                securityScheme.addExtension(CommonConstant.OpenAPI.X_VALUE, authKeyInfo.getAuthKey());

                operation.setSecurity(
                        Collections.singletonList(new SecurityRequirement().addList(CommonConstant.OpenAPI.API_KEY)));
                openAPI.components(new Components().addSecuritySchemes(CommonConstant.OpenAPI.API_KEY, securityScheme));
            }
        } else if (authInfo != null && !CollectionUtils.isEmpty(authInfo.getIamCredentials())) {
            if (authInfo.getScope() == AuthInfo.ScopeEnum.IAM) {
                SecurityScheme securityScheme = new SecurityScheme();
                securityScheme.addExtension(CommonConstant.OpenAPI.X_PROJECT_ID,
                        toolEntity.getAuthInfo().getIamCredentials().get(CommonConstant.PROJECT_ID));
                securityScheme.addExtension(CommonConstant.OpenAPI.X_DOMAIN_ID,
                        toolEntity.getAuthInfo().getIamCredentials().get(CommonConstant.DOMAIN_ID));
                operation.setSecurity(
                        Collections.singletonList(new SecurityRequirement().addList(CommonConstant.OpenAPI.IAM)));
                openAPI.components(new Components().addSecuritySchemes(CommonConstant.OpenAPI.IAM, securityScheme));
            }
        } else if (authInfo != null && AuthInfo.ScopeEnum.HIS_IAM.equals(authInfo.getScope())) {
            SecurityScheme securityScheme = new SecurityScheme();
            securityScheme.addExtension(CommonConstant.OpenAPI.IAM_URL,
                    toolEntity.getAuthInfo().getHisIamInfo().getIamUrl());
            securityScheme.addExtension(CommonConstant.OpenAPI.IAM_ACCOUNT,
                    toolEntity.getAuthInfo().getHisIamInfo().getIamAccount());
            securityScheme.addExtension(CommonConstant.OpenAPI.IAM_PROJECT,
                    toolEntity.getAuthInfo().getHisIamInfo().getIamProject());
            securityScheme.addExtension(CommonConstant.OpenAPI.IAM_SECRET,
                    toolEntity.getAuthInfo().getHisIamInfo().getIamSecret());
            securityScheme.addExtension(CommonConstant.OpenAPI.IAM_ENTERPRISE,
                    toolEntity.getAuthInfo().getHisIamInfo().getIamEnterprise());
            operation.setSecurity(
                    Collections.singletonList(new SecurityRequirement().addList(CommonConstant.OpenAPI.HIS_IAM)));
            openAPI.components(new Components().addSecuritySchemes(CommonConstant.OpenAPI.HIS_IAM, securityScheme));
        } else if (authInfo != null && AuthInfo.ScopeEnum.SGOV.equals(authInfo.getScope())) {
            SecurityScheme securityScheme = new SecurityScheme();
            securityScheme.addExtension(CommonConstant.OpenAPI.SGOV_URL,
                    toolEntity.getAuthInfo().getHisSgov().getSgovUrl());
            securityScheme.addExtension(CommonConstant.OpenAPI.APP_ID,
                    toolEntity.getAuthInfo().getHisSgov().getAppId());
            securityScheme.addExtension(CommonConstant.OpenAPI.CREDENTIAL,
                    toolEntity.getAuthInfo().getHisSgov().getCredential());
            operation.setSecurity(
                    Collections.singletonList(new SecurityRequirement().addList(CommonConstant.OpenAPI.HIS_SGOV)));
            openAPI.components(new Components().addSecuritySchemes(CommonConstant.OpenAPI.HIS_SGOV, securityScheme));
        } else if (authInfo != null && AuthInfo.ScopeEnum.CUSTOM_IAM.equals(authInfo.getScope())) {
            SecurityScheme securityScheme = new SecurityScheme();
            buildIAMSecurityScheme(authInfo, securityScheme);

            operation.setSecurity(
                    Collections.singletonList(new SecurityRequirement().addList(CommonConstant.OpenAPI.CUSTOM_IAM)));
            openAPI.components(new Components().addSecuritySchemes(CommonConstant.OpenAPI.CUSTOM_IAM, securityScheme));
        }

        // 生成openapi文件内容
        String json = Json.pretty(openAPI);
        if (StringUtils.isEmpty(json)) {
            log.error("open api to json string failed");
            throw new AgentStudioException(StudioError.OPEN_API_GEN_FAILED);
        }
        log.debug("open api generated: \n{}", json);
        return json;
    }

    private static void parseInputSchema(String inputSchemaStr, List<Parameter> parameters, SchemaConfig requestBody) {
        if (StringUtils.isEmpty(inputSchemaStr)) {
            // inputSchemaStr可以为空
            return;
        }

        // 遍历第一层的inputSchema
        SchemaConfig inputSchema = JsonUtils.json2ObjQuietly(inputSchemaStr, SchemaConfig.class);
        if (inputSchema == null) {
            log.error("parse input schema failed");
            throw new AgentStudioException(StudioError.TOOL_INPUT_SCHEMA_INVALID);
        }
        if (inputSchema.getProperties() == null) return;

        for (Map.Entry<String, SchemaConfig> entry : inputSchema.getProperties().entrySet()) {
            SchemaConfig schemaConfig = entry.getValue();
            String name = entry.getKey();
            String location = schemaConfig.getLocation();
            if (ToolParamLocation.HEADER.location.equals(location)) {
                // 请求参数列表中的header
                parameters.add(new Parameter().name(name)
                        .in(CommonConstant.OpenAPI.IN_HEADER)
                        .description(schemaConfig.getDescription())
                        .schema(new StringSchema()));
            } else if (ToolParamLocation.QUERY.location.equals(location)) {
                // 请求参数列表中的query
                parameters.add(new Parameter().name(name)
                        .in(CommonConstant.OpenAPI.IN_QUERY)
                        .description(schemaConfig.getDescription())
                        .schema(new StringSchema()));
            } else if (ToolParamLocation.BODY.location.equals(location)) {
                // 请求参数列表中的body
                requestBody.getProperties().put(name, schemaConfig);
                if (inputSchema.getRequired().contains(name)) {
                    requestBody.getRequired().add(name);
                }
            } else if (ToolParamLocation.PATH.location.equals(location)) {
                // 请求参数列表中的path
                parameters.add(new Parameter().name(name)
                        .in(CommonConstant.OpenAPI.IN_PATH)
                        .description(schemaConfig.getDescription())
                        .schema(new StringSchema()));
            }
        }
    }

    /**
     * 将插件数据库中实体转换成Tool对象，其中鉴权秘钥值做加密，header信息做解密
     *
     * @param toolEntity 插件在数据库的实体
     * @return Tool
     */
    private Tool convertToolFromToolEntity(ToolEntity toolEntity) {
        Tool tool = new Tool();
        BeanUtils.copyProperties(toolEntity, tool);
        tool.setIsOutputList(toolEntity.getIsOutputList());
        tool.setIsInputList(toolEntity.getIsInputList());
        tool.setVisibility(toolEntity.getVisibility());
        tool.setTestStatus(TestStatus.fromCode(toolEntity.getTestStatus()).name());
        tool.setCreateTime(toolEntity.getCreatedOn());
        tool.setUpdateTime(toolEntity.getUpdatedOn());
        if (Objects.equals(toolEntity.getCustomizeNode(), 1)) {
            tool.setCustomizeNode(true);
        }

        // 插件鉴权信息中的秘钥值需要加密处理
        tool.setAuthInfo(anonymizeAuthInfo(tool.getAuthInfo()));
        if (tool.getCredentials() != null) {
            // 隐藏AuthKey
            tool.getCredentials().setAuthKeys(null);
        }
        return tool;
    }

    public void checkToolInfo(String toolName, String inputSchema, String outputSchema, String visibility,
                               String intfType) {
        // 检查visibility取值
        if (!StringUtils.isEmpty(visibility)
                && !Arrays.stream(VisibilityEnum.values()).anyMatch(item -> item.getValue().equals(visibility))) {
            log.error("Visibility value:{} is invalid.", visibility);
            throw new AgentStudioException(StudioError.INVALID_VISIBILITY, visibility);
        }

        // 新建插件的name不在黑名单中（预置插件、知识检索插件）
        if (StringUtils.isNotBlank(toolNameBlackList)
                && Arrays.asList(toolNameBlackList.split(",")).contains(toolName)) {
            log.error("Fail to create tool for duplicate tool name [{}] in black list", toolName);
            throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
        }

        // 工具的 input_schema、output_schema 格式需要满足模型要求
        try {
            if (!JsonSchemaUtils.isJsonSchemaValid(inputSchema, maxPropNum, maxPropDepth, true)) {
                log.error("The format of tool input schema is invalid: {}", inputSchema);
                throw new AgentStudioException(StudioError.TOOL_INPUT_SCHEMA_INVALID);
            }
        } catch (AgentStudioException exception) {
            log.error("The format of tool input schema is invalid: {}", inputSchema);
            throw new AgentStudioException(StudioError.TOOL_INPUT_SCHEMA_INVALID,
                    i18nUtil.getMessage("openjiuwen.02401002") + " " + exception.getMessage());
        }
        try {
            // 非流式插件才校验output格式
            if (!(!StringUtils.isEmpty(intfType)
                    && CommonConstant.Plugin.INTF_TYPE_STREAMING.equalsIgnoreCase(intfType))) {
                if (!JsonSchemaUtils.isJsonSchemaValid(outputSchema, maxPropNum, maxPropDepth, false)) {
                    log.error("The format of tool output schema is invalid: {}", outputSchema);
                    throw new AgentStudioException(StudioError.TOOL_OUTPUT_SCHEMA_INVALID);
                }
            }
        } catch (AgentStudioException exception) {
            log.error("The format of tool output schema is invalid: {}", outputSchema);
            throw new AgentStudioException(StudioError.TOOL_OUTPUT_SCHEMA_INVALID,
                    i18nUtil.getMessage("openjiuwen.02401003") + " " + exception.getMessage());
        }
    }

    private String getToolType(String projectId) {
        return isOpTenant(projectId) ? ToolType.INNER.type : ToolType.CUSTOM.type;
    }

    private List<ToolEntity> getToolEntityList(String projectId, String workspaceId, SearchCriteria searchCriteria) {
        if (searchCriteria == null) {
            searchCriteria = new SearchCriteria();
        }
        // 根据环境变量excludeInnerTools构造不可见的预置插件id列表用于过滤
        if (!StringUtils.isBlank(excludeInnerTools)) {
            List<String> excludeIds =
                    Stream.of(excludeInnerTools.split(CommonConstant.SEPARATOR)).map(p -> PRESET + p).toList();
            searchCriteria.setExcludeIds(excludeIds);
        }

        // 新增检索类型all（当前工作流Agent节点搜索全部插件时使用），同时搜索预置和自定义插件
        if (!StringUtils.isBlank(searchCriteria.getType()) && ToolType.ALL.type.equals(searchCriteria.getType())) {
            return toolMapper.selectAllBySearchCriteria(projectId, opSvcProjectId, workspaceId, null, searchCriteria);
        } else {
            if (ToolType.INNER.type.equals(searchCriteria.getType())) {
                return toolMapper.selectPresetPluginByProjectIdAndSearchCriteria(getToolProjectId(projectId, searchCriteria), null, searchCriteria, workspaceId);
            }
            searchCriteria.setWorkspaceId(workspaceId);
            return toolMapper.selectByProjectIdAndSearchCriteria(getToolProjectId(projectId, searchCriteria), null, searchCriteria, workspaceId);
        }
    }

    private String getToolProjectId(String projectId, SearchCriteria searchCriteria) {
        if (Objects.isNull(searchCriteria) || StringUtils.isBlank(searchCriteria.getType())) {
            return projectId;
        }
        return ToolType.INNER.type.equals(searchCriteria.getType()) ? opSvcProjectId : projectId;
    }

    private AuthInfo encryptedAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                if (StringUtils.isBlank(authKeyInfo.getAuthKey())
                        || CommonConstant.ANONYMIZED_TEXT.equals(authKeyInfo.getAuthKey())) {
                    return null;
                }
                authKeyInfo.setAuthKey(encryptionAdapter.encrypt(authKeyInfo.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
            }
        }
        return authInfo;
    }

    // 对于服务级鉴权，需要把authKey值设置为null，0625修改为"******"与其他服务统一
    private AuthInfo anonymizeAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            authInfo.getAuthKeys().forEach(authKeyInfo -> authKeyInfo.setAuthKey(maskKey(authKeyInfo.getAuthKey())));
        }
        return authInfo;
    }

    private String maskKey(String key) {
        if (StringUtils.isBlank(key)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }

        String decryptedKey;
        try {
            // 换成新架构的适配器解密
            decryptedKey = encryptionAdapter.decrypt(key);
        } catch (AgentStudioException e) {
            // 加容错防止跨租户或密钥失效导致整个列表接口 500 崩溃
            log.warn("Failed to decrypt tool key for masking. Key might be deleted or invalid.");
            return CommonConstant.ANONYMIZED_TEXT;
        } catch (Exception e) {
            log.warn("Unexpected error when decrypting tool key for masking.", e);
            return CommonConstant.ANONYMIZED_TEXT;
        }

        if (StringUtils.isBlank(decryptedKey)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }

        if (decryptedKey.length() == 1) {
            return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1);
        }

        return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1,
                CommonConstant.ANONYMIZED_TEXT.length() - 1) + decryptedKey.charAt(decryptedKey.length() - 1);
    }

    private boolean isOpTenant(String projectId) {
        return opSvcProjectId.equals(projectId);
    }

    /**
     * 校验内置工具是否存在
     *
     */
    public void checkInnerToolPermission(String toolId) {
        PluginEntity toolEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(toolId, null, null);
        if (Objects.isNull(toolEntity)) {
            log.error("Tool {} does not exist.", toolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
    }

    public void buildIAMSecurityScheme(AuthInfo authInfo, SecurityScheme securityScheme) {
        PluginIAMAuthInfo customIamCredentials = authInfo.getCustomIamCredentials();
        if (Objects.isNull(customIamCredentials)) {
            return;
        }
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_URL,
                customIamCredentials.getIamUrl());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_DOMAIN,
                customIamCredentials.getIamDomain());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_PROJECT,
                customIamCredentials.getIamProject());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_USER,
                customIamCredentials.getIamUser());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_PASSWORD,
                customIamCredentials.getIamPassword());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_AK,
                customIamCredentials.getIamAk());
        securityScheme.addExtension(CommonConstant.OpenAPI.CUSTOM_IAM_SK,
                customIamCredentials.getIamSk());
    }
}

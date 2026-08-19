/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TestStatus;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.bo.WfImportDataWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExtraMsg;
import com.openjiuwen.studio.agent.manager.dto.GetPluginVersionQo;
import com.openjiuwen.studio.agent.common.dto.auth.HisIamInfo;
import com.openjiuwen.studio.agent.common.dto.auth.HisSgov;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListPluginsQo;
import com.openjiuwen.studio.agent.manager.dto.ListToolsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginRsp;
import com.openjiuwen.studio.agent.manager.dto.ParsePluginReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateRsp;
import com.openjiuwen.studio.agent.common.dto.auth.PluginIAMAuthInfo;
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.plugin.BasicInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.IsInputList;
import com.openjiuwen.studio.agent.manager.dto.plugin.IsOutputList;
import com.openjiuwen.studio.agent.manager.dto.plugin.PluginDTO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolDependency;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolIntfType;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolOutputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolTestStatus;
import com.openjiuwen.studio.agent.manager.dto.plugin.UrlInfo;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolExportEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginExportEntity;
import com.openjiuwen.studio.agent.manager.enums.PluginCallModeEnum;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.enums.VisibilityEnum;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.OldPluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.AgentCommonService;
import com.openjiuwen.studio.agent.manager.service.IPluginService;
import com.openjiuwen.studio.agent.manager.service.ToolManagementService;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginAdapterImpl;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.IconNameCheckUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.parser.OpenAPIV3Parser;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.commons.lang3.math.NumberUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.core.io.Resource;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Slf4j
@Service
public class PluginService implements IPluginService {
    /**
     * 预置插件前缀
     */
    private static final String PRESET = "preset_";

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${tool.name.black-list}")
    private String toolNameBlackList;

    @Value("${tool.default-icon}")
    private String defaultIcon;

    @Value("${tool.maxnum:30}")
    private int toolMaxNum;

    @Value("${inner.exclude-tools}")
    private String excludeInnerTools;

    @Value("${export.max-length}")
    private int importMaxLen;

    @Value("${tool.max-release-version-size}")
    private int releaseMaxSize;

    @Value("${tool.plugin-publish:false}")
    private boolean pluginChoice;

    @Value("${allow-plugin-cross-permission-query:false}")
    private boolean allowPluginCrossPermissionQuery;

    @Value("${spring.is-soft-delete: true}")
    private Boolean isSoftDelete;

    @Value("${isHcs:false}")
    private Boolean isHcs;

    @Value("${asset.plugin.free.trial-quota-limit:10}")
    private int pluginMaxFreeTrialTimes;

    private static final String PLUGIN_FREE_TRIAL_USAGE_QUOTA_RW_LOCK_FORMAT
        = "agent.manager.asset.plugin.free.trial.usage.quota.rw.lock.asset_%s.month_%d.domain_%s.lock";

    private static final String PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT
        = "agent.manager.asset.plugin.free.trial.usage.quota.asset_%s.month_%d.domain_%s";

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private ToolManagementService toolManagementService;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private OldPluginMapper oldPluginMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private MessageSource messageSource;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private IPluginBase pluginBase;

    private static int TESTFAIL = 0;

    private static int TESTSUCCESS = 1;

    public static final String FUNCTION_PATH = "/%s/fgs/functions/%s/invocations";

    public static final Pattern pattern = Pattern.compile("\\{([^}]+)\\}");

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private PluginAdapterImpl pluginAdapterImpl;

    @Autowired
    private MgObsService obsService;

    @Override
    @Transactional
    @OperationLog(
            operationType = OperationType.CREATE,
            resourceType = "Tool",
            description = "批量创建工具",
            resourceId = "-1"  // 批量操作无法确定单一资源ID
    )
    public BatchCreatePluginToolRsp batchCreateTool(String projectId, String workspaceId,
        BatchCreatePluginToolReq body) {
        log.info("operation log {}: start to batch create tool", projectId);
        List<String> toolIds = new ArrayList<>();

        for (CreatePluginToolReq toolRequest : body.getTools()) {
            log.info("operation log {}: start to create tool", projectId);
            PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(toolRequest.getPluginId(),
                projectId, workspaceId);
            if (pluginEntity == null) {
                log.error("Fail to create tool for plugin [{}] not exist under tenant [{}]", toolRequest.getPluginId(),
                    projectId);
                throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
            }
            PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);

            String toolId = addTool(toolRequest, pluginDTO);
            toolIds.add(toolId);
        }

        return new BatchCreatePluginToolRsp().setIds(toolIds);
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Plugin",
        description = "创建插件",
        resourceId = "-1",
        resourceName = "body.pluginDisplayName"
    )
    public CreatePluginToolRsp createPlugin(String projectId, String workspaceId, CreatePluginToolReq body) {
        log.info("operation log {}: start to create plugin", projectId);
        PluginDTO pluginDTO = buildPluginEntity(projectId, workspaceId, body);

        log.info("Checking for duplicate display name - DisplayName: {}, WorkspaceId: {}",
            pluginDTO.getPluginDisplayName(), workspaceId);
        int existDisplayName = pluginMapper.selectByDisplayNameAndWorkspaceId(pluginDTO.getPluginDisplayName(),
            workspaceId);
        if (existDisplayName > 0) {
            log.warn("Display name already exists - DisplayName: {}, WorkspaceId: {}", pluginDTO.getPluginDisplayName(),
                workspaceId);
            throw new AgentStudioException(StudioError.PLUGIN_EN_NAME_ALREADY_EXIST);
        }

        log.info("Inserting new plugin into database - PluginId: {}", pluginDTO.getPluginId());
        try {
            pluginMapper.insert(pluginBase.transformDTOtoNewEntity(pluginDTO));
        } catch (DuplicateKeyException e) {
            log.error("Fail to create tool for duplicate tool name [{}] under tenant [{}]", body.getToolDisplayName(),
                projectId);
            throw new AgentStudioException(StudioError.PLUGIN_ID_ALREADY_EXIST);
        }

        log.info("Plugin created successfully - PluginId: {}", pluginDTO.getPluginId());
        return new CreatePluginToolRsp().setToolId(pluginDTO.getPluginId());
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
    public CreatePluginToolRsp createTool(String projectId, String workspaceId, CreatePluginToolReq body) {
        log.info("operation log {}: start to create tool", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(body.getPluginId(), projectId,
            workspaceId);
        if (pluginEntity == null) {
            log.error("Fail to create tool for plugin [{}] not exist under tenant [{}]", body.getPluginId(), projectId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);

        String toolId = addTool(body, pluginDTO);

        return new CreatePluginToolRsp().setToolId(toolId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Tool",
        description = "在工具中创建API",
        resourceId = "toolId",
        resourceName = ""
    )
    public BaseResp createToolOpenAPIById(String projectId, String workspaceId, String pluginId, String toolId) {
        // 根据ID插件调测
        log.info("operation log {}: start to create plugin openapi", projectId);
        ToolEntity newTool = pluginBase.buildToolByPlugin(projectId, workspaceId, pluginId, toolId);
        // 根据toolEntity对象转化为OpenAPI定义并上传到obs
        toolManagementService.uploadToolOpenAPI(newTool);
        return new BaseResp().setCode(200).setMessage("success").setData(newTool.getToolId());
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Plugin",
        description = "删除插件",
        resourceId = "pluginId",
        resourceName = ""
    )
    public CommonDeleteRsp deletePlugin(String projectId, String pluginId, String workspaceId) {
        log.info("operation log {}: start to delete plugin", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);
        if (Objects.isNull(pluginEntity)) {
            log.info("No plugin entity found, plugin ID: {}, project ID: {}.", pluginId, projectId);
            return null;
        }

        shareInnerService.cancelPluginShared(projectId, workspaceId, pluginId);
        // 设置关联的资源为已失效
        mappingMapper.updateValidByResourceId(pluginId);
        pluginMapper.updatePluginShareStatus(pluginId, 0);

        if (isSoftDelete) {
            log.info("start to soft delete plugin and version, pluginId = {}", pluginId);
            agentCommonService.softDeleteReleaseVersionByAppId(pluginId);   // 处理Agent版本表，迁移到新的表，旧数据删除
            pluginMapper.copyToHistoryTool(pluginId, projectId, UUID.randomUUID().toString());
        } else {
            log.info("start to delete plugin and version, pluginId = {}", pluginId);
            releaseVersionMapper.deleteByAppId(pluginId);   // 删除已发布的版本
        }
        // 删除已发布的版本的obs文件
        List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(pluginId);
        releaseVersions.forEach(releaseVersion -> mgObsService.deleteObsFile(releaseVersion.getDslPath()));
        // 删除插件
        pluginMapper.deleteByPrimaryKey(pluginId, projectId);
        log.info("delete tool version pluginId = {}", pluginId);
        return new CommonDeleteRsp().setId(pluginId);
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Plugin",
        description = "删除插件版本",
        resourceId = "pluginId",
        resourceName = ""
    )
    public CommonDeleteRsp deletePluginVersion(String projectId, String versionId, String pluginId,
        String workspaceId) {
        log.info("operation log {}: start to delete plugin version", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);
        if (Objects.isNull(pluginEntity)) {
            return null;
        }

        // 自定义工具，需要校验用户id
        if (!isOpTenant(projectId) && !Objects.equals(pluginEntity.getCreatorId(),
            RequestContextUtils.getRequestUserId())) {
            throw new AgentStudioException(StudioError.NO_PERMISSION_DELETE_TOOL);
        }
        shareInnerService.cancelPluginVersionShared(projectId, workspaceId, pluginId, versionId);
        // 删除OBS资源
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(pluginId, versionId);
        mgObsService.deleteObsFile(releaseVersion.getDslPath());
        // 设置关联的资源为已失效
        mappingMapper.updateValidByResourceIdAndVersionId(pluginId, versionId);
        // 删除已发布的版本
        releaseVersionMapper.deleteByAppIdAndVersionId(pluginId, versionId);

        // 更新last_version_id
        List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(pluginId);
        if (releaseVersions == null || releaseVersions.isEmpty()) {
            // 更新发布状态
            toolMapper.updatePublished(pluginId, projectId, 0);
        }
        Optional<String> latestVersion = releaseVersions.stream()
            .map(ReleaseVersion::getVersionId)
            .max(Comparator.naturalOrder());
        toolMapper.updateLastVersionId(pluginId, projectId, latestVersion.orElse(null));

        log.info("delete tool version pluginId = {}, toolVersion={}", pluginId, versionId);
        return new CommonDeleteRsp().setId(pluginId).setVersionId(versionId);
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
    public BaseResp deleteTool(String projectId, String pluginId, String toolId, String workspaceId) {
        log.info("operation log {}: start to delete tool", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);
        if (pluginEntity == null) {
            log.error("Fail to delete tool for plugin [{}] not exist under tenant [{}]", pluginId, projectId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);

        subTool(toolId, pluginDTO);
        mappingMapper.updateValidByResourceIdAndVersionId(pluginEntity.getPluginId() + "#" + toolId, null);

        return new BaseResp().setCode(200).setMessage("success");
    }

    /**
     * 插件导出
     *
     * @param projectId projectId
     * @param workspaceId 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    @Override
    public Resource exportplugins(String projectId, String workspaceId, ExportParams body) {
        log.info("operation log {}: start to export plugin", projectId);
        List<String> pluginIds = body.getToolIds();
        PluginExportEntity pluginExportEntity = new PluginExportEntity();
        // 判断是否超出最大导出数量限制
        if (pluginIds.size() > importMaxLen) {
            log.error("Exceeded the maximum export limit. The maximum number of exports is {}.", importMaxLen);
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE, importMaxLen);
        }
        Set<String> uniquePluginIds = new HashSet<>(pluginIds);
        // 插件越权校验
        validPlugins(uniquePluginIds, projectId, workspaceId);

        // 插件导出逻辑
        StringBuilder tempJson = new StringBuilder();
        List<PluginEntity> pluginEntitys = pluginMapper.batchSelectByPrimaryKeyAndWorkspace(uniquePluginIds, projectId,
            workspaceId);
        try {
            for (PluginEntity pluginEntity : pluginEntitys) {
                // 从数据库查询该插件配置信息
                PluginDTO plugin = pluginBase.transformEntityToDTO(pluginEntity);
                if (plugin == null) {
                    throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
                }
                decryptedExportPlugin(plugin);
                if (!isHcs) {
                    decryptedAuthInfo(plugin);
                }
                pluginExportEntity.setMetadata(pluginBase.transformDTOtoNewEntity(plugin));
                pluginExportEntity.setImportType(CommonConstant.PLUGIN);
                tempJson.append(jacksonObjectMapper.writeValueAsString(pluginExportEntity)).append("\n");
            }
            byte[] bytes = tempJson.toString().getBytes(StandardCharsets.UTF_8);

            // 处理响应体
            ResponseModel.TransferResource resource = new ResponseModel.TransferResource(
                new ByteArrayInputStream(bytes));
            resource.setFilename("plugins.jsonl");
            resource.setLength((long) bytes.length);
            return resource;
        } catch (Exception e) {
            log.error("Failed to export the plug-in.", e);
            throw new AgentStudioException(StudioError.TOOL_EXPORT_FILE);
        }
    }

    /**
     * 导出插件时进行解密
     *
     * @param plugin 插件信息
     */
    public void decryptedExportPlugin(PluginDTO plugin) {
        List<ToolInfo> toolInfoList = plugin.getToolRequestInfo().getToolsInfoList();
        for (ToolInfo toolInfo : toolInfoList) {
            if (!Objects.isNull(plugin.getToolRequestInfo())) {
                Map<String, String> headers = toolInfo.getHeaders();
                if (MapUtils.isEmpty(headers)) {
                    return;
                }

                for (Map.Entry<String, String> entry : headers.entrySet()) {
                    String key = entry.getKey();
                    String value = entry.getValue();
                    // 新代码：调用适配器
                    // 适配器内部逻辑：KMS解密 -> 失败则SCC解密 -> 还失败则认为本身就是明文，返回原值
                    // 所以这里不需要 try-catch 了
                    String decrypted = encryptionAdapter.decrypt(value);

                    // 只有当解密后的值不为空时才更新（通常 NodeAdapter 会保证不返回 null，但加个判断更稳健）
                    if (StringUtils.isNotEmpty(decrypted)) {
                        headers.put(key, decrypted);
                    } else {
                        // 极端情况：如果原来的 value 不为空，但解出来是空，说明出问题了，保留原值
                        log.warn("Decryption returned empty for plugin [{}], keeping original.",
                            plugin.getPluginDisplayName());
                    }
                }

            }
        }
    }

    public void decryptedAuthInfo(PluginDTO plugin) {
        AuthInfo authInfo = plugin.getAuthInfo();
        anonymizeAuthInfo(authInfo);
    }

    @Override
    public BaseResp getPluginVersion(String projectId, String versionId, String pluginId,
        GetPluginVersionQo getPluginVersionQo) {
        log.info("operation log {}: start to get plugin version", projectId);
        PluginEntity pluginEntity = pluginBase.getPluginEntityByVersion(pluginId, versionId);
        adapterOldPlugin(pluginEntity);
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);
        if (!Strings.CS.equals(pluginDTO.getType(), ToolType.INNER.type) && !Strings.CS.equals(
            pluginEntity.getWorkspaceId(), getPluginVersionQo.getWorkspaceId())) {
            // 判断是否共享资源，共享资源也可查询
            ShareScopeEntity shareScopeEntity = shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(pluginId,
                ThreadLocalUtils.getWorkspaceId());
            // 非空表示跨空间引用查询，检查版本号是否被共享
            if (Objects.nonNull(shareScopeEntity)) {
                // 检查工作流是否被授权
                ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(
                    pluginId);
                if (!shareResourceEntity.getVersionList().contains(versionId)) {
                    log.error(
                        "getToolVersion, request project id: {} workspace id: {}, tool project id {} workspace id {}",
                        projectId, getPluginVersionQo.getWorkspaceId(), pluginEntity.getProjectId(),
                        pluginEntity.getWorkspaceId());
                    throw new AgentStudioException(StudioError.PLUGIN_PRIVILEGE_ERROR, pluginEntity.getProjectId());
                }
            } else {
                log.error("getToolVersion, request project id: {} workspace id: {}, tool project id {} workspace id {}",
                    projectId, getPluginVersionQo.getWorkspaceId(), pluginEntity.getProjectId(),
                    pluginEntity.getWorkspaceId());
                throw new AgentStudioException(StudioError.PLUGIN_PRIVILEGE_ERROR, pluginEntity.getProjectId());
            }
        }
        return new BaseResp().setCode(200).setMessage("success").setData(pluginDTO);
    }

    public void adapterOldPlugin(PluginEntity pluginEntity) {
        PluginEntity plugin = pluginMapper.selectInfo(pluginEntity.getPluginId());
        if (StringUtils.isEmpty(pluginEntity.getWorkspaceId())) {
            pluginEntity.setWorkspaceId(plugin.getWorkspaceId());
        }
        if (StringUtils.isEmpty(pluginEntity.getType())) {
            pluginEntity.setType(plugin.getType());
        }
    }

    // 对于服务级鉴权，需要把authKey值设置为null，0625修改为"******"与其他服务统一
    public AuthInfo anonymizeAuthInfo(AuthInfo authInfo) {
        log.info(">>>anonymizeAuthInfo start");
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            log.info(">>>anonymizeAuthInfo service");
            authInfo.getAuthKeys().forEach(authKeyInfo -> authKeyInfo.setAuthKey(maskKey(authKeyInfo.getAuthKey())));
        }
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.HIS_IAM.equals(authInfo.getScope())) {
            log.info(">>>anonymizeAuthInfo his_iam");
            authInfo.getHisIamInfo().setIamSecret(maskKey(authInfo.getHisIamInfo().getIamSecret()));
        }
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SGOV.equals(authInfo.getScope())) {
            log.info(">>>anonymizeAuthInfo sgov");
            authInfo.getHisSgov().setCredential(maskKey(authInfo.getHisSgov().getCredential()));
        }
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.CUSTOM_IAM.equals(authInfo.getScope())) {
            log.info(">>>anonymizeAuthInfo custom_iam");
            PluginIAMAuthInfo customIamCredentials = authInfo.getCustomIamCredentials();
            if (StringUtils.isNotBlank(customIamCredentials.getIamPassword())) {
                authInfo.getCustomIamCredentials().setIamPassword(maskKey(customIamCredentials.getIamPassword()));
            } else {
                authInfo.getCustomIamCredentials().setIamSk(maskKey(customIamCredentials.getIamSk()));
            }
        }
        return authInfo;
    }

    private String maskKey(String key) {
        if (StringUtils.isBlank(key)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }

        String decryptedKey;
        try {
            // 尝试解密，如果当前账号 domain_id 不匹配、没权限、或密钥被删，这里会抛异常
            decryptedKey = encryptionAdapter.decrypt(key);
        } catch (AgentStudioException e) {
            // 捕获跨租户、无权限等解密失败的异常，保护列表不崩溃
            log.warn("Decrypt failed for masking (possibly cross-domain or deleted key).");
            return CommonConstant.ANONYMIZED_TEXT;
        } catch (Exception e) {
            log.warn("Unexpected error when decrypting key for masking.", e);
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

    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Plugin",
        description = "导入插件",
        resourceId = "-1",
        resourceName = ""
    )
    public ImportRsp importplugins(String workspaceId, String projectId, MultipartFile file, String importIds) {
        log.info("operation log {}: start to import plugin", projectId);
        List<String> importIdList = Arrays.asList(importIds.split(","));
        ImportRsp importRsp = new ImportRsp();
        WfImportDataWrapper wfImportDataWrapper = new WfImportDataWrapper();
        wfImportDataWrapper.setImportPluginList(importIdList);
        try (BufferedReader bufferedReader = new BufferedReader(
            new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;

            // 逐行读取导入文件中的jsonl
            while ((line = bufferedReader.readLine()) != null) {
                PluginExportEntity plugin = new PluginExportEntity();
                JsonNode node = jacksonObjectMapper.readTree(line);
                JsonNode requestInfoNode = node.get("metadata").get("request_info");

                if (requestInfoNode != null) {
                    if (requestInfoNode.isObject() && !requestInfoNode.has("basic_info")) {
                        ToolExportEntity tool = jacksonObjectMapper.readValue(line,
                            new TypeReference<ToolExportEntity>() { });
                        PluginEntity pluginEntity = pluginBase.transformTool2Plugin(tool.getMetadata());
                        plugin.setMetadata(pluginEntity);
                        plugin.setImportType(tool.getImportType());
                    } else {
                        plugin = jacksonObjectMapper.readValue(line, new TypeReference<PluginExportEntity>() { });
                    }
                }
                String pluginId = plugin.getMetadata().getPluginId();

                // 如果环境中是否已存在该插件配置，且用户不选择覆盖，则continue
                if (!importIdList.contains(pluginId)) {
                    continue;
                }

                // 插件以 traceId 标识同一资源。已存在时导入会执行覆盖更新，需要与新增导入分别计数。
                boolean pluginExists = isPluginExist(projectId, workspaceId, plugin.getMetadata());

                // id冲突，则随机生成一个uuid
                checkAndUpdateUuid(workspaceId, projectId, pluginId, plugin);

                // 导入插件逻辑
                boolean succeeded = importPluginsHandler(projectId, workspaceId, plugin.getMetadata(),
                    wfImportDataWrapper.getPluginsOfAuth());
                recordImportResult(wfImportDataWrapper, pluginId, plugin.getMetadata().getPluginId(), pluginExists,
                    succeeded);
                if (!succeeded) {
                    log.error("Failed to import tool:{}", plugin);
                }
            }
            buildImportRsp(importRsp, wfImportDataWrapper);
        } catch (Exception e) {
            log.error("Failed to import the plug-in.", e);
            throw new AgentStudioException(StudioError.TOOL_IMPORT_FILE);
        }
        return importRsp;
    }

    public void checkAndUpdateUuid(String workspaceId, String projectId, String pluginId, PluginExportEntity plugin) {
        if (!Objects.isNull(toolMapper.selectWithoutStatus(pluginId, null, null)) && !isPluginExist(projectId,
            workspaceId, plugin.getMetadata())) {
            plugin.getMetadata().setPluginId(UUID.randomUUID().toString());
        }
    }

    /**
     * @param projectId   projectId
     * @param domainId    domainId
     * @param pluginId    pluginId
     * @param workspaceId workspaceId
     * @return
     */
    @Override
    public BaseResp incrementPluginFreeTrialUsageQuota(String projectId, String domainId, String pluginId,
        String workspaceId) {
        RedisLock writePluginUsageLockKey = null;
        log.info(">>>incrementPluginFreeTrialUsageQuota pluginId {}", pluginId);
        try {
            writePluginUsageLockKey = redisClient.getLock(getPluginFreeTrialUsageQuotaRwLockKey(domainId, pluginId));
            log.info(">>>incrementPluginFreeTrialUsageQuota writePluginUsageLockKey success");
            if (writePluginUsageLockKey.tryLock(Duration.ofSeconds(10))) {
                String pluginFreeTrialUsageRecordsVal = redisClient.get(
                    getPluginFreeTrialUsageQuotaKey(domainId, pluginId));

                if (StringUtils.isBlank(pluginFreeTrialUsageRecordsVal)) {
                    log.info("None usage records of plugin {} for domain {} in month_{}.", pluginId, domainId,
                        LocalDate.now().getMonthValue());
                    redisClient.set(getPluginFreeTrialUsageQuotaKey(domainId, pluginId), "1",
                        Duration.ofMillis(getPluginFreeTrialRecordsListKeyTtlMills()));
                    log.info("Add usage record success.");
                    return new BaseResp().setMessage("success").setCode(1);
                }
                int usageQuotaCntInFreeTrial = NumberUtils.toInt(pluginFreeTrialUsageRecordsVal);

                if (usageQuotaCntInFreeTrial >= pluginMaxFreeTrialTimes) {
                    log.info(
                        "Usage records count has reach the max free trial times limit {}, current usage quota: {}.",
                        pluginMaxFreeTrialTimes, usageQuotaCntInFreeTrial);
                    log.info("Don't increment usage quota. Domain: {}, Plugin: {}", domainId, pluginId);
                    return new BaseResp().setMessage("fail").setCode(0);
                } else {
                    redisClient.set(getPluginFreeTrialUsageQuotaKey(domainId, pluginId),
                        String.valueOf(usageQuotaCntInFreeTrial + 1),
                        Duration.ofMillis(getPluginFreeTrialRecordsListKeyTtlMills()));
                    log.info("Add usage record success. Domain: {}, Plugin: {}, usageQuotaCnt {}.", domainId, pluginId,
                        usageQuotaCntInFreeTrial);
                    return new BaseResp().setMessage("success").setCode(1);
                }
            } else {
                log.info("Failed to get lock when add Plugin trial usage records. Domain: {}, Plugin: {}", domainId,
                    pluginId);
                return new BaseResp().setMessage("fail").setCode(0);
            }
        } catch (Exception e) {
            log.error("Failed to add Plugin trial usage records.", e);
            return new BaseResp().setMessage("fail").setCode(0);
        } finally {
            if (writePluginUsageLockKey != null) {
                writePluginUsageLockKey.unlock();
            }
        }
    }

    private String getPluginFreeTrialUsageQuotaKey(String domainId, String pluginId) {
        return String.format(Locale.ROOT, PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT, pluginId,
            LocalDate.now().getMonthValue(), domainId);
    }

    private String getPluginFreeTrialUsageQuotaRwLockKey(String domainId, String pluginId) {
        return String.format(Locale.ROOT, PLUGIN_FREE_TRIAL_USAGE_QUOTA_RW_LOCK_FORMAT, pluginId,
            LocalDate.now().getMonthValue(), domainId);
    }

    private long getPluginFreeTrialRecordsListKeyTtlMills() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime firstDayOfNextMonth = now.with(TemporalAdjusters.firstDayOfNextMonth()).with(LocalTime.MAX);
        return Duration.between(now, firstDayOfNextMonth).toMillis();
    }

    @Override
    public VersionListRsp listPluginVersions(String projectId, String pluginId, String workspaceId) {
        log.info("operation log {}: start to list all plugin version", projectId);
        checkPluginPermission(projectId, workspaceId, pluginId);
        return agentCommonService.listVersions(pluginId, releaseMaxSize);
    }

    public void checkPluginPermission(String projectId, String workspaceId, String pluginId) {
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);
        if (Objects.isNull(pluginEntity)) {
            log.error("Plugin {} projectId {} workspaceId {} does not exist.", pluginId, projectId, workspaceId);
            throw new AgentStudioException(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, pluginId, projectId, workspaceId);
        }
    }

    void recordImportResult(WfImportDataWrapper wrapper, String originalPluginId, String resultPluginId,
        boolean pluginExists, boolean succeeded) {
        if (!succeeded) {
            wrapper.getFailedIds().add(originalPluginId);
            return;
        }
        wrapper.getSucceedIds().add(resultPluginId);
        if (pluginExists) {
            wrapper.getUpdatedIds().add(resultPluginId);
        } else {
            wrapper.getImportedIds().add(resultPluginId);
        }
    }

    void buildImportRsp(ImportRsp importRsp, WfImportDataWrapper wfImportDataWrapper) {
        importRsp.setSucceedIds(wfImportDataWrapper.getSucceedIds());
        importRsp.setFailedIds(wfImportDataWrapper.getFailedIds());
        importRsp.setSucceedLen(wfImportDataWrapper.getSucceedIds().size());
        importRsp.setFailedLen(wfImportDataWrapper.getFailedIds().size());
        importRsp.setImportedLen(wfImportDataWrapper.getImportedIds().size());
        importRsp.setUpdatedLen(wfImportDataWrapper.getUpdatedIds().size());
        importRsp.setSkippedLen(wfImportDataWrapper.getSkippedIds().size());
        importRsp.setCount(importRsp.getSucceedLen() + importRsp.getFailedLen() + importRsp.getSkippedLen());
        importRsp.setAuthPluginsMsg(new ArrayList<>(wfImportDataWrapper.getPluginsOfAuth()));
        importRsp.setInnerPluginsMsg(new ArrayList<>(wfImportDataWrapper.getInnerPluginsMsg()));
        importRsp.setAuthMcpsMsg(new ArrayList<>(wfImportDataWrapper.getMcpsOfAuth()));
    }

    /**
     * 判断当前userId下是否存在该插件
     *
     * @param projectId projectId
     * @param plugin 插件
     * @return Boolean
     */
    public Boolean isPluginExist(String projectId, String targetWorkspaceId, PluginEntity plugin) {
        List<PluginEntity> pluginEntity = pluginMapper.selectByTraceIdAndWorkspaceId(projectId, targetWorkspaceId,
            plugin.getTraceId());
        return !CollectionUtils.isEmpty(pluginEntity);
    }

    /**
     * 导入单个插件
     *
     * @param projectId projectId
     * @param plugin 需要导入的插件对象
     * @return boolean 是否导入成功
     */
    public boolean importPluginsHandler(String projectId, String targetWorkspaceId, PluginEntity plugin,
        Set<ExtraMsg> pluginsOfAuth) {
        // 校验插件地址
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(plugin);
        String url = pluginDTO.getToolRequestInfo().getBasicInfo().getProtocol() + "://"
            + pluginDTO.getToolRequestInfo().getBasicInfo().getHost();
        try {
            // op 账号也校验，projectid直接传空
            urlCheckUtils.checkUrl(null, url);
        } catch (Exception e) {
            log.error(String.format("Failed to import plugin: %s", plugin.getPluginId()), e);
            return false;
        }

        plugin.setProjectId(projectId);
        plugin.setWorkspaceId(targetWorkspaceId);
        plugin.setCreator(opSvcProjectId.equals(projectId)
            ? CommonConstant.DEFAULT_USERNAME
            : RequestContextUtils.getRequestUserName());
        plugin.setCreatorId(RequestContextUtils.getRequestUserId());
        plugin.setDomainId(RequestContextUtils.getRequestUserDomainId());
        Date date = new Date();
        plugin.setCreatedOn(date);
        plugin.setUpdatedOn(date);
        plugin.setCallMode("api");
        String testStatus = plugin.getTestStatus();
        if (testStatus != null && !testStatus.isEmpty()) {
            testStatus = plugin.getTestStatus().replaceAll("(?<=\"test_status\":)\\d+", "2");
            plugin.setTestStatus(testStatus);
        } else {
            plugin.setTestStatus("[{\"tool_id\":\"0\",\"test_status\":2}]");
        }
        plugin.setLastVersionId(null);
        // 适配安全问题，可能会传入明文的秘钥
        adapterPlugin(plugin);

        // 插件ChineseName或者DisplayName为空时，值选则其中不为空的那个
        if (StringUtils.isEmpty(plugin.getPluginChineseName()) && StringUtils.isEmpty(plugin.getPluginDisplayName())) {
            return false;
        }
        if (StringUtils.isEmpty(plugin.getPluginDisplayName())) {
            plugin.setPluginDisplayName(plugin.getPluginChineseName());
        }
        if (StringUtils.isEmpty(plugin.getPluginChineseName())) {
            plugin.setPluginChineseName(plugin.getPluginDisplayName());
        }

        // 名称重复校验
        int existChineseName = pluginMapper.selectByChineseNameAndWorkspaceIdAndProjectId(plugin.getPluginChineseName(),
            targetWorkspaceId, plugin.getPluginId());
        int existDisplayName = pluginMapper.selectByDisplayNameAndWorkspaceIdAndProjectId(plugin.getPluginDisplayName(),
            targetWorkspaceId, plugin.getPluginId());
        if (existChineseName > 0) {
            int seq = 1;
            while (true) {
                String candidateName = plugin.getPluginChineseName() + "_" + seq;
                if (pluginMapper.selectByChineseNameAndWorkspaceIdAndProjectId(candidateName, targetWorkspaceId,
                    plugin.getPluginId()) == 0) {
                    plugin.setPluginChineseName(candidateName);
                    break;
                }
                seq++;
            }
        }
        if (existDisplayName > 0) {
            int seq = 1;
            while (true) {
                String candidateName = plugin.getPluginDisplayName() + "_" + seq;
                if (pluginMapper.selectByDisplayNameAndWorkspaceIdAndProjectId(candidateName, targetWorkspaceId,
                    plugin.getPluginId()) == 0) {
                    plugin.setPluginDisplayName(candidateName);
                    break;
                }
                seq++;
            }
        }

        // 设置唯一插件name
        String pluginDisplayName = plugin.getPluginDisplayName();
        SearchCriteria searchCriteria = new SearchCriteria();
        searchCriteria.setWorkspaceId(targetWorkspaceId);
        List<PluginEntity> pluginEntityList = pluginMapper.selectByProjectIdAndSearchCriteria(projectId, null,
            searchCriteria, targetWorkspaceId);
        if (pluginEntityList != null && !pluginEntityList.isEmpty()) {
            Set<String> currentNames = pluginEntityList.stream()
                .map(PluginEntity::getPluginDisplayName)
                .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));
            if (currentNames.contains(pluginDisplayName) && !plugin.getPluginId()
                .equals(
                    pluginMapper.selectByNameAndWorkspaceIdAndProjectId(pluginDisplayName, targetWorkspaceId, projectId)
                        .getPluginId())) {
                pluginDisplayName = subName(pluginDisplayName, CommonConstant.NAME_MAX_LEN);
                int index = 1;
                while (currentNames.contains(pluginDisplayName + Constants.UNDERLINE_STR + index)
                    && !plugin.getPluginId()
                    .equals(pluginMapper.selectByNameAndWorkspaceIdAndProjectId(
                            pluginDisplayName + Constants.UNDERLINE_STR + index, targetWorkspaceId, projectId)
                        .getPluginId())) {
                    index++;
                }
                plugin.setPluginDisplayName(pluginDisplayName + Constants.UNDERLINE_STR + index);
            }
        }

        // 若已存在该配置走覆盖逻辑，否则插入到数据库中
        try {
            if (isPluginExist(projectId, targetWorkspaceId, plugin)) {
                // 插件visibility字段不允许修改
                plugin.setVisibility(null);
                pluginMapper.updateByPrimaryKeySelective(plugin);
            } else {
                pluginMapper.insert(plugin);
            }
        } catch (Exception e) {
            log.error(String.format("Failed to import plugin: %s", plugin.getPluginId()), e);
            return false;
        }

        // 含有鉴权信息的插件
        if (plugin.getAuthInfo().getScope() != null && AuthInfo.ScopeEnum.SERVICE.equals(
            plugin.getAuthInfo().getScope())) {
            ExtraMsg authMsg = new ExtraMsg().setId(plugin.getPluginId()).setName(plugin.getPluginDisplayName());
            pluginsOfAuth.add(authMsg);
        }

        // 导入插件版本
        if (StringUtils.isNotEmpty(plugin.getVersionId()) && !importPluginVersion(projectId, plugin)) {
            return false;
        }

        log.info("Succeed to import plugin: {}", plugin.getPluginId());
        return true;
    }

    public void adapterPlugin(PluginEntity pluginEntity) {
        log.info(">>>adapterPlugin start plugin id {}", pluginEntity.getPluginId());
        if (ObjectUtils.isEmpty(pluginEntity.getAuthInfo()) || ObjectUtils.isEmpty(
            pluginEntity.getAuthInfo().getAuthKeys())) {
            return;
        }

        for (AuthKeyInfo entry : pluginEntity.getAuthInfo().getAuthKeys()) {
            if (!checkIsDecrypt(entry.getAuthKey())) {
                log.info(">>>adapterPlugin plaintext plugin id {}", pluginEntity.getPluginId());
                // 修改：使用 adapter 加密
                entry.setAuthKey(
                    encryptionAdapter.encrypt(entry.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
            }
        }
    }

    private boolean checkIsDecrypt(String authKey) {
        if (StringUtils.isBlank(authKey)) {
            return false;
        }

        // 尝试解密并比较 (主要针对 SCC 旧数据)
        String decrypted = encryptionAdapter.decrypt(authKey);

        // 如果解密后的文本和原文本不同，说明它是一个有效的密文（被成功解开了）
        // 如果相同，说明它是明文（或者是一个解密失败的密文，但因为上面已经拦截了 KMS 格式，这里剩下的主要是 SCC 失败或纯明文）
        return !Strings.CS.equals(authKey, decrypted);
    }

    @Override
    public PluginListRsp listPlugins(String projectId, ListPluginsQo listPluginsQo) {
        log.info("operation log {}: start to list plugin", projectId);
        List<PluginEntity> pluginEntitys = getToolEntityList(projectId, listPluginsQo.getWorkspaceId(),
            convertSearchCriteriaFromListToolsQo(listPluginsQo), listPluginsQo.getEntryPoint());

        List<PluginDTO> plugins = new ArrayList<>();
        pluginEntitys.forEach(pluginEntity -> {
            if (pluginEntity == null) {
                throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, "can not find any plugins");
            }
            PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);
            if (CommonConstant.USER.equals(pluginDTO.getVisibility()) && !pluginDTO.getCreatorId()
                .equals(RequestContextUtils.getRequestUserId())) {
                return;
            }
            // 内置免费额度插件
            if (ToolType.INNER.type.equals(pluginDTO.getType()) && pluginDTO.getIsFree() != null
                && pluginDTO.getIsFree() == 1) {
                pluginDTO.setLimit(pluginMaxFreeTrialTimes);
                try {
                    String domainId = RequestContextUtils.getRequestUserDomainId();
                    String pluginFreeTrialUsageRecords = redisClient.get(
                        getPluginFreeTrialUsageQuotaKey(domainId, pluginDTO.getPluginId()));

                    if (StringUtils.isBlank(pluginFreeTrialUsageRecords)) {
                        log.info("None plugin free trial quota record stored, return zero as usage quota. "
                            + "Domain: {}, plugin: {}.", domainId, pluginDTO.getPluginId());
                        pluginDTO.setUsage(0);
                    }
                    pluginDTO.setUsage(NumberUtils.toInt(pluginFreeTrialUsageRecords));
                } catch (Exception e) {
                    throw new AgentStudioException(StudioError.PLUGIN_FREE_TRIAL_USAGE_QUOTA_ERROR, e.getMessage());
                }
            }
            // 内置插件host限制
            if (ToolType.INNER.type.equals(pluginDTO.getType()) && !opSvcProjectId.equals(projectId)) {
                pluginDTO.getToolRequestInfo().getBasicInfo().setHost(null);
                pluginDTO.getToolRequestInfo().getToolsInfoList().forEach(toolInfo -> toolInfo.setUrl(null));
            }
            plugins.add(pluginDTO);
        });

        PluginListRsp pluginListRsp = new PluginListRsp();

        // 根据语言处理返回结果
        Locale locale = LanguageUtils.getLanguageLocale();
        plugins.forEach(tool -> {
            if (CommonConstant.DEFAULT_USERNAME.equals(tool.getCreator())) {
                tool.setCreator(
                    messageSource.getMessage("tool.creator.official", null, CommonConstant.DEFAULT_USERNAME, locale));
            }
            tool.setAuthInfo(anonymizeAuthInfo(tool.getAuthInfo()));
            if (Strings.CI.equals(ToolType.INNER.type, tool.getType())) {
                tool.getToolRequestInfo().getBasicInfo().setHost(null);
            }
        });
        pluginListRsp.setPluginList(plugins.subList(listPluginsQo.getOffset(),
            Math.min(listPluginsQo.getLimit() + listPluginsQo.getOffset(), plugins.size())));
        pluginListRsp.setCount((long) plugins.size());
        return pluginListRsp;
    }

    // 导入插件版本
    public boolean importPluginVersion(String projectId, PluginEntity pluginEntity) {
        String pluginId = pluginEntity.getPluginId();
        String versionId = pluginEntity.getVersionId();
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(pluginId, versionId);
        if (existVersion != null) {
            return true;
        }

        try {
            // 版本不存在导入版本
            String versionName = "v" + new Date().getTime();
            releasePluginVersionHandler(pluginEntity, versionId, versionName, "");

            // 更新最新版本号
            ToolEntity oldTool = toolMapper.selectByPrimaryKey(pluginEntity.getPluginId(), projectId);
            String oldVersionId = oldTool.getLastVersionId();
            if (StringUtils.isEmpty(oldVersionId) || Long.parseLong(versionId) > Long.parseLong(oldVersionId)) {
                oldTool.setLastVersionId(versionId);
                toolMapper.updateByPrimaryKeySelective(oldTool);
            }
        } catch (Exception e) {
            log.error("import tool:{}, version:{} failed", pluginId, versionId);
            return false;
        }
        return true;
    }

    /**
     * 发布插件对象
     *
     * @param pluginEntity plugin对象
     * @param versionId versionId
     * @param versionName 版本名称
     * @param versionNote 版本备注
     * @return 发布版本对象
     */
    public ReleaseVersion releasePluginVersionHandler(PluginEntity pluginEntity, String versionId, String versionName,
        String versionNote) {
        String pluginId = pluginEntity.getPluginId();
        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion.setVersionId(
            StringUtils.isBlank(versionId) ? String.valueOf(System.currentTimeMillis()) : versionId);

        // 发布到OBS
        pluginEntity.setLastVersionId(null);
        String releaseDslPath = mgObsService.uploadObsFile(pluginId,
            pluginId + Constants.UNDERLINE_STR + releaseVersion.getVersionId(), CommonConstant.PLUGIN,
            JsonUtils.toJson(pluginEntity), CommonConstant.DSL_STR);
        releaseVersion.setDslPath(releaseDslPath);

        // 新版本insert t_release_version
        pluginEntity.setPublished(1);
        pluginMapper.updateByPrimaryKeySelective(pluginEntity);
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setReleasedOn(new Date());

        releaseVersion.setVersionName(versionName);
        releaseVersion.setVersionNote(versionNote);

        releaseVersion.setAppType(CommonConstant.PLUGIN_TYPE);
        releaseVersion.setStatus(CommonConstant.NORMAL);

        releaseVersion.setAppId(pluginEntity.getPluginId());

        releaseVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersion.setCreatorId(RequestContextUtils.getRequestUserId());

        releaseVersionMapper.insert(releaseVersion);
        return releaseVersion;
    }

    /**
     * 同名时预处理截断name
     *
     * @param name 原始名称
     * @return 截断后的名称
     */
    private String subName(String name, int length) {
        if (name.length() > length) {
            name = name.substring(0, length);
        }
        return name;
    }

    @Override
    public BaseResp listTools(String projectId, ListToolsQo listToolsQo) {
        log.info("operation log {}: start to list tools", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(listToolsQo.getId(), projectId,
            listToolsQo.getWorkspaceId());
        if (pluginEntity == null) {
            log.error("Fail to list tool for plugin [{}] not exist under tenant [{}]", listToolsQo.getId(), projectId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);

        return new BaseResp().setCode(200).setMessage("success").setData(pluginDTO);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Plugin",
        description = "修改插件",
        resourceId = "pluginId",
        resourceName = "body.toolDisplayName"
    )
    public ModifyPluginRsp modifyPlugin(String projectId, String workspaceId, String pluginId, ModifyPluginReq body) {
        log.info("operation log {}: start to modify plugin", projectId);
        List<PluginEntity> pluginEntities = pluginMapper.selectByWorkspaceIdAndProjectId(projectId, workspaceId,
            pluginId);
        pluginEntities.forEach(pluginEntity -> {
            String toolDisplayName = pluginEntity.getPluginDisplayName();
            if (StringUtils.isEmpty(pluginEntity.getTestStatus())) {
                pluginEntity.setTestStatus("[{\"tool_id\":\"0\",\"test_status\":2}]");
            }
            if (Strings.CS.equals(toolDisplayName, body.getToolDisplayName())) {
                throw new AgentStudioException(StudioError.PLUGIN_EN_NAME_ALREADY_EXIST);
            }
        });

        // 工具参数信息校验
        checkUrl(body.getRequestInfo(), null);
        checkToolInfo(body.getToolDisplayName(), null);
        PluginEntity oldPlugin = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);

        if (Objects.isNull(oldPlugin)) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST,
                String.format("plugin id %s not exist", pluginId));
        }
        if (!Strings.CS.equals(body.getCallMode(), oldPlugin.getCallMode())) {
            log.error("callMode can not modify, pluginId:{}", pluginId);
            throw new AgentStudioException(StudioError.PLUGIN_CALL_MODE_CANNOT_MODIFFY);
        }
        if (Strings.CS.equals(body.getCallMode(), PluginCallModeEnum.API.getCode())) {
            // 预置插件支持修改auth描述
            if (ToolType.INNER.type.equals(oldPlugin.getType()) && Boolean.TRUE.equals(oldPlugin.getAuthRequired())) {
                clearAuthInfo(body.getAuthInfo());
                if (!Objects.isNull(body.getAuthInfo()) && (
                    AuthInfo.ScopeEnum.HIS_IAM.equals(body.getAuthInfo().getScope()) || AuthInfo.ScopeEnum.SGOV.equals(
                        body.getAuthInfo().getScope()))) {
                    body.setAuthInfo(encryptedAuthInfo(body.getAuthInfo()));
                }
            } else {
                body.setAuthInfo(encryptedAuthInfo(body.getAuthInfo()));
            }
        }

        PluginEntity newPlugin = ConvertPluginFromModifyBody(body, oldPlugin);

        // 发布为自定义节点校验
        Integer customizeNode = newPlugin.getCustomizeNode();
        if (customizeNode != null && !customizeNode.equals(oldPlugin.getCustomizeNode())) {
            agentCommonService.publishCustomizeNodeCheck(projectId, pluginId, oldPlugin.getLastVersionId(),
                customizeNode);
        }

        String icon;
        if (body.getIcon() == null) {
            icon = oldPlugin.getIcon();
        } else {
            IconNameCheckUtils.validaIconName(body.getIcon());
            newPlugin.setIconName(body.getIcon());
            icon = ImageBase64Utils.getImageBase64(body.getIcon(), mgObsService);
        }
        newPlugin.setIcon(icon);

        newPlugin.setPluginId(pluginId);
        newPlugin.setProjectId(projectId);
        newPlugin.setDomainId(RequestContextUtils.getRequestUserDomainId());
        urlCheckUtils.checkUrl(null, body.getMetadata());
        newPlugin.setMetadata(body.getMetadata());
        newPlugin.setAuthRequired(body.isAuthRequired());
        try {
            pluginMapper.updateByPrimaryKeySelective(newPlugin);
        } catch (DuplicateKeyException exception) {
            log.error("Fail to modify tool for duplicate tool name [{}] under tenant [{}]", body.getToolDisplayName(),
                projectId);
            throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
        }
        return new ModifyPluginRsp().setToolId(pluginId);
    }

    @Override
    public BaseResp parsePlugin(String projectId, String workspaceId, ParsePluginReq body) {
        String data = body.getContent();
        if (StringUtils.isBlank(data)) {
            throw new AgentStudioException(StudioError.OPENAPI_FILE_NOT_EXIST);
        }
        OpenAPI openAPI;
        OpenAPIV3Parser parser = new OpenAPIV3Parser();
        try {
            openAPI = parser.readContents(data).getOpenAPI();
            PluginDTO pluginDTO = pluginBase.transformOpenAPI2Plugin(openAPI);
            return new BaseResp().setCode(200).setMessage("success").setData(pluginDTO);
        } catch (Exception e) {
            log.error("parse plugin error,{}", e.getMessage());
            throw new AgentStudioException(StudioError.OPENAPI_PARSE_FAILED, e.getMessage());
        }
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Tool",
        description = "修改工具",
        resourceId = "toolId",
        resourceName = "body.toolDisplayName"
    )
    public BaseResp modifyTool(String projectId, String workspaceId, String toolId, CreatePluginToolReq body) {
        log.info("operation log {}: start to modify tool", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(body.getPluginId(), projectId,
            workspaceId);
        if (pluginEntity == null) {
            log.error("Fail to modify tool for plugin [{}] not exist under tenant [{}]", body.getPluginId(), projectId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }

        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);

        updateTool(body, pluginDTO, toolId);

        return new BaseResp().setCode(200).setMessage("success");
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Plugin",
        description = "发布插件版本",
        resourceId = "pluginId",
        resourceName = "body.versionName"
    )
    public VersionInfo releasePluginVersion(String projectId, String pluginId, String workspaceId,
        CreateVersionReq body) {
        log.info("operation log {}: start to release plugin version", projectId);
        // 检查是否测试成功
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(pluginId, projectId,
            workspaceId);

        // 校验用户id
        String requestUserId = RequestContextUtils.getRequestUserId();
        if (!isOpTenant(projectId) && !Objects.equals(pluginEntity.getCreatorId(), requestUserId)) {
            log.error("{} try to publish a tool create by {}", requestUserId, pluginEntity.getCreatorId());
            throw new AgentStudioException(StudioError.NO_CREATOR_PERMISSION);
        }

        // 校验发布版本数量
        List<ReleaseVersion> releaseVersionList = releaseVersionMapper.selectByAppId(pluginId);
        if (releaseVersionList.size() > releaseMaxSize) {
            log.error("release version reach the max size {}", releaseVersionList.size());
            throw new AgentStudioException(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT);
        }

        // 如果request_info包含basic_info，一切按下面进行，否则要转为toolentity再继续操作
        String requestInfo = pluginEntity.getRequestInfo();
        JSONObject requestInfoJson;
        try {
            requestInfoJson = JSON.parseObject(requestInfo);
        } catch (Exception e) {
            log.error("parse request_info error: {}", requestInfo, e);
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        ReleaseVersion releaseVersion = new ReleaseVersion();
        if (requestInfoJson.containsKey("basic_info")) {
            // 新格式，直接继续执行后续逻辑
            log.info("new format detected, continue with current logic");
            // 发布版本
            releaseVersion = releasePluginVersionHandler(pluginEntity, null, body.getVersionName(),
                body.getVersionNote());

            // 更新最新版本号
            PluginEntity newPluginEntity = new PluginEntity();
            newPluginEntity.setPluginId(pluginEntity.getPluginId());
            newPluginEntity.setProjectId(pluginEntity.getProjectId());
            newPluginEntity.setLastVersionId(releaseVersion.getVersionId());
            newPluginEntity.setPublished(1);
            pluginMapper.updateByPrimaryKeySelective(newPluginEntity);
        } else {
            // 旧格式
            log.info("old format detected, need to convert to new format");
            ToolEntity toolEntity = oldPluginMapper.selectOldPluginById(pluginEntity.getPluginId());
            toolEntity.setCredentialStatus(pluginEntity.getCredentialStatus());
            releaseVersion = toolManagementService.releaseToolVersionHandler(toolEntity, null, body.getVersionName(),
                body.getVersionNote());

            // 更新最新版本号
            ToolEntity newToolEntity = new ToolEntity();
            newToolEntity.setToolId(toolEntity.getToolId());
            newToolEntity.setProjectId(toolEntity.getProjectId());
            newToolEntity.setLastVersionId(releaseVersion.getVersionId());
            newToolEntity.setPublished(1);
            toolMapper.updateByPrimaryKeySelective(newToolEntity);
        }
        log.info("release a new tool version {}", releaseVersion);
        return releaseVersion.convertToInfo();
    }

    @Override
    public BaseResp retrievePlugin(String projectId, String pluginId, String workspaceId) {

        log.info("operation log {}: start to get single plugin", projectId);
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(pluginId, null,
            workspaceId);
        if (pluginEntity == null) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST,
                String.format("plugin id %s not exist", pluginId));
        }
        if (ToolType.INNER.type.equals(pluginEntity.getType()) && !Strings.CS.equals(workspaceId,
            pluginEntity.getWorkspaceId())) {
            if (pluginEntity.getPublished() == null || pluginEntity.getPublished() != 1) {
                throw new AgentStudioException(StudioError.PLUGIN_NO_PERMISSION_VIEW, String.format("%s.", pluginId));
            }
        }
        if (ToolType.CUSTOM.type.equals(pluginEntity.getType()) && !Strings.CS.equals(workspaceId,
            pluginEntity.getWorkspaceId())) {
            throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION,
                String.format("%s.", pluginId));
        }
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntity);
        pluginDTO.setAuthInfo(anonymizeAuthInfo(pluginDTO.getAuthInfo()));
        pluginDTO.setToolDependencyList(new ArrayList<>());

        // 构建tool_dependency_list字段
        // 统计口径与引用插件列表(listResourceRelations)保持完全一致，仅维度不同：
        // 此处按工具(pluginId#toolId)分组计数，引用插件列表按插件粒度计数；
        // 去重键、valid/工作空间/JOIN等筛选条件均与 listResourceRelations 相同。
        Map<String, Long> workflowCountByTool = countReferencedAppsByTool(
            mappingMapper.selectByResourceIdAndVersionId(pluginDTO.getPluginId(), null, workspaceId, "workflow", null));
        Map<String, Long> agentCountByTool = countReferencedAppsByTool(
            mappingMapper.selectByResourceIdAndVersionId(pluginDTO.getPluginId(), null, workspaceId, "agent", null));
        for (ToolInfo toolInfo : pluginDTO.getToolRequestInfo().getToolsInfoList()) {
            String toolResourceId = pluginDTO.getPluginId() + "#" + toolInfo.getToolId();
            pluginDTO.getToolDependencyList()
                .add(ToolDependency.builder()
                    .toolId(toolInfo.getToolId())
                    .dependencyOnAgent(agentCountByTool.getOrDefault(toolResourceId, 0L))
                    .dependencyOnWorkflow(workflowCountByTool.getOrDefault(toolResourceId, 0L))
                    .build());
        }
        // 内置免费额度插件
        if (ToolType.INNER.type.equals(pluginDTO.getType()) && pluginDTO.getIsFree() != null
            && pluginDTO.getIsFree() == 1) {
            pluginDTO.setLimit(pluginMaxFreeTrialTimes);
            try {
                String domainId = RequestContextUtils.getRequestUserDomainId();
                String pluginFreeTrialUsageRecords = redisClient.get(
                    getPluginFreeTrialUsageQuotaKey(domainId, pluginDTO.getPluginId()));

                if (StringUtils.isBlank(pluginFreeTrialUsageRecords)) {
                    log.info("None plugin free trial quota record stored, return zero as usage quota. "
                        + "Domain: {}, plugin: {}.", domainId, pluginDTO.getPluginId());
                    pluginDTO.setUsage(0);
                }
                pluginDTO.setUsage(NumberUtils.toInt(pluginFreeTrialUsageRecords));
            } catch (Exception e) {
                throw new AgentStudioException(StudioError.PLUGIN_FREE_TRIAL_USAGE_QUOTA_ERROR, e.getMessage());
            }
        }
        // 内置插件host限制
        if (ToolType.INNER.type.equals(pluginDTO.getType()) && !opSvcProjectId.equals(projectId)) {
            String host = pluginDTO.getToolRequestInfo().getBasicInfo().getHost();
            InetAddress[] addresses = new InetAddress[0];
            try {
                addresses = InetAddress.getAllByName(host);
            } catch (UnknownHostException e) {
                // 如果无法解析域名 隐藏
                pluginDTO.getToolRequestInfo().getBasicInfo().setHost("******");
                updateHost(pluginDTO);
            }
            for (InetAddress addr : addresses) {
                // 检查是否为内网IP
                if (urlCheckUtils.isInternalIp(addr, projectId)) {
                    pluginDTO.getToolRequestInfo().getBasicInfo().setHost("******");
                    updateHost(pluginDTO);
                }
            }
        }
        return new BaseResp().setCode(200).setMessage("success").setData(pluginDTO);
    }

    /**
     * 将引用映射按工具维度(resource_id，形如 pluginId#toolId)分组，值为去重后的应用id集合。
     * 同一应用的多个版本/多个节点重复引用只保留一个appId，保证按应用数计数。
     */
    /**
     * 按工具维度统计被引用次数。SQL 用 selectByResourceIdAndVersionId（与引用插件列表同一条），
     * 前缀匹配捞取 pluginId 及 pluginId#* 的全部行（含单后缀 pluginId#toolId 与
     * 历史脏数据双后缀 pluginId#toolId#toolId）。分组时将 resource_id 规范化为 pluginId#toolId
     * （取首个 # 后到第二个 # 前的段作为 toolId），使双后缀行也能正确归到对应工具；
     * 去重键与 RelationManagementService#getDeduplicationKey 完全一致
     * (appId|appVersion|resourceId|resourceVersion，resourceId 取完整原值)，
     * 保证与引用插件列表口径相同，仅因按工具分组而维度不同。
     */
    private Map<String, Long> countReferencedAppsByTool(List<MappingEntity> mappingEntities) {
        return mappingEntities.stream()
            .collect(Collectors.groupingBy(entity -> normalizeToolResourceId(entity.getResourceId()),
                Collectors.collectingAndThen(
                    Collectors.mapping(this::getDeduplicationKey, Collectors.toSet()),
                    set -> (long) set.size())));
    }

    /**
     * 将 resource_id 规范化为 pluginId#toolId。
     * pluginId#toolId → pluginId#toolId；pluginId#toolId#toolId → pluginId#toolId；
     * 裸 pluginId（无工具后缀）原样返回。
     */
    private String normalizeToolResourceId(String resourceId) {
        int first = resourceId.indexOf('#');
        if (first < 0) {
            return resourceId;
        }
        String tail = resourceId.substring(first + 1);
        int second = tail.indexOf('#');
        String toolId = second < 0 ? tail : tail.substring(0, second);
        return resourceId.substring(0, first) + "#" + toolId;
    }

    private String getDeduplicationKey(MappingEntity entity) {
        return entity.getAppId() + "|" + (entity.getAppVersion() == null ? "" : entity.getAppVersion())
            + "|" + entity.getResourceId() + "|"
            + (entity.getResourceVersion() == null ? "" : entity.getResourceVersion());
    }

    public void updateHost(PluginDTO pluginDTO) {
        log.info(">>>updateHost update host");
        pluginDTO.getToolRequestInfo().getToolsInfoList().stream().forEach(toolInfo -> toolInfo.setUrl("******"));
    }

    private List<PluginEntity> getToolEntityList(String projectId, String workspaceId, SearchCriteria searchCriteria,
        String entryPoint) {
        if (searchCriteria == null) {
            searchCriteria = new SearchCriteria();
        }
        // 根据环境变量excludeInnerTools构造不可见的预置插件id列表用于过滤
        if (!StringUtils.isBlank(excludeInnerTools)) {
            List<String> excludeIds = Stream.of(excludeInnerTools.split(CommonConstant.SEPARATOR))
                .map(p -> PRESET + p)
                .toList();
            searchCriteria.setExcludeIds(excludeIds);
        }

        // 新增检索类型all（当前工作流Agent节点搜索全部插件时使用），同时搜索预置和自定义插件
        if (!StringUtils.isBlank(searchCriteria.getType()) && ToolType.ALL.type.equals(searchCriteria.getType())) {
            return pluginMapper.selectAllBySearchCriteria(projectId, opSvcProjectId, workspaceId, null, searchCriteria);
        } else {
            if (pluginChoice) {
                searchCriteria.setPublished(null);
            }
            if (allowPluginCrossPermissionQuery) {
                searchCriteria.setWorkspaceId(null);
            }
            if (ToolType.INNER.type.equals(searchCriteria.getType())) {
                return pluginMapper.selectByProjectIdAndSearchCriteria(getToolProjectId(projectId, searchCriteria),
                    null, searchCriteria, workspaceId);
            }
            searchCriteria.setWorkspaceId(workspaceId);
            if (allowPluginCrossPermissionQuery && !Strings.CS.equals("partial", entryPoint)) {
                searchCriteria.setWorkspaceId(null);
            }
            if (StringUtils.isNotEmpty(searchCriteria.getId())) {
                searchCriteria.setType(null);
                return pluginMapper.selectByProjectIdAndSearchCriteria(getToolProjectId(projectId, searchCriteria),
                    null, searchCriteria, null);
            }
            return pluginMapper.selectByProjectIdAndSearchCriteria(getToolProjectId(projectId, searchCriteria), null,
                searchCriteria, workspaceId);
        }
    }

    private String getToolProjectId(String projectId, SearchCriteria searchCriteria) {
        if (Objects.isNull(searchCriteria) || StringUtils.isBlank(searchCriteria.getType())) {
            return projectId;
        }
        return ToolType.INNER.type.equals(searchCriteria.getType()) ? opSvcProjectId : projectId;
    }

    private SearchCriteria convertSearchCriteriaFromListToolsQo(ListPluginsQo listPluginsQo) {
        return new SearchCriteria().setId(listPluginsQo.getId())
            .setIds(listPluginsQo.getIds())
            .setName(StrUtils.filterSpecialWords(listPluginsQo.getEnName()))
            .setToolChineseName(StrUtils.filterSpecialWords(listPluginsQo.getCnName()))
            .setToolDesc(StrUtils.filterSpecialWords(listPluginsQo.getDesc()))
            .setType(listPluginsQo.getType())
            .setIntfType(listPluginsQo.getIntfType())
            .setCreator(listPluginsQo.getCreator())
            .setUserId(listPluginsQo.getCreatorId())
            .setPublished(listPluginsQo.isPublished())
            .setCallMode(listPluginsQo.getCallMode())
            .setCustomizeNode(listPluginsQo.isCustomizeNode())
            .setLabel(listPluginsQo.getLabel())
            .setCategory(listPluginsQo.getCategory());
    }

    private String addTool(CreatePluginToolReq createPluginToolReq, PluginDTO pluginDTO) {
        checkToolNum(pluginDTO);

        // 名字校验
        Set<String> englisNameSet = pluginDTO.getToolRequestInfo()
            .getToolsInfoList()
            .stream()
            .map(ToolInfo::getToolDisplayName)
            .collect(Collectors.toSet());

        if (englisNameSet.contains(createPluginToolReq.getToolDisplayName())) {
            throw new AgentStudioException(StudioError.TOOL_EN_NAME_ALREADY_EXIST);
        }

        String toolId = generate16BitId();
        ToolInfo newToolInfo = new ToolInfo();

        // 提取path
        newToolInfo.setToolId(toolId);
        newToolInfo.setToolDisplayName(createPluginToolReq.getToolDisplayName());
        newToolInfo.setToolChineseName(createPluginToolReq.getToolChineseName());
        newToolInfo.setToolDesc(createPluginToolReq.getToolDesc());
        newToolInfo.setPath(
            getToolPath(pluginDTO.getToolRequestInfo().getBasicInfo(), createPluginToolReq.getRequestInfo().getUrl()));
        newToolInfo.setMethod(createPluginToolReq.getRequestInfo().getMethod().toString());
        pluginDTO.getToolRequestInfo().getToolsInfoList().add(newToolInfo);

        ToolInputSchema toolInputSchema = ToolInputSchema.builder()
            .toolId(toolId)
            .inputSchema(createPluginToolReq.getInputSchema())
            .build();
        pluginDTO.getToolInputSchemaList().add(toolInputSchema);

        ToolOutputSchema toolOutputSchema = ToolOutputSchema.builder()
            .toolId(toolId)
            .outputSchema(createPluginToolReq.getOutputSchema())
            .build();
        pluginDTO.getToolOutputSchemaList().add(toolOutputSchema);

        ToolIntfType toolIntfType = ToolIntfType.builder()
            .toolId(toolId)
            .intfType(createPluginToolReq.getIntfType())
            .build();
        pluginDTO.getToolIntfTypeList().add(toolIntfType);

        ToolTestStatus toolTestStatus = ToolTestStatus.builder()
            .toolId(toolId)
            .testStatus(TestStatus.UNKNOWN.getCode())
            .build();
        pluginDTO.getToolTestStatusList().add(toolTestStatus);
        IsInputList isInputList = IsInputList.builder()
            .toolId(toolId)
            .isList(createPluginToolReq.isIsInputList())
            .build();

        IsOutputList outputList = IsOutputList.builder()
            .toolId(toolId)
            .isList(createPluginToolReq.isIsOutputList())
            .build();

        pluginDTO.getIsInputList().add(isInputList);
        pluginDTO.getIsOutputList().add(outputList);

        PluginEntity pluginEntity = pluginBase.transformDTOtoNewEntity(pluginDTO);

        pluginBase.validateDuplicateInputSchema(pluginDTO.getToolInputSchemaList(), pluginDTO.getToolRequestInfo());

        pluginEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());

        pluginMapper.updateByPrimaryKeySelective(pluginEntity);

        return toolId;
    }

    private void checkToolNum(PluginDTO pluginDTO) {
        // tool数量校验
        if (pluginDTO.getToolRequestInfo().getToolsInfoList() == null) {
            pluginDTO.getToolRequestInfo().setToolsInfoList(new ArrayList<>());
        }
        if (pluginDTO.getToolRequestInfo().getToolsInfoList().size() >= toolMaxNum) {
            log.error("Tool number exceeds the limit");
            throw new AgentStudioException(StudioError.TOOL_NUM_EXCEEDS_LIMIT);
        }
    }

    private void updateTool(CreatePluginToolReq createPluginToolReq, PluginDTO pluginDTO, String toolId) {

        if (pluginDTO.getToolRequestInfo().getToolsInfoList() == null) {
            pluginDTO.getToolRequestInfo().setToolsInfoList(new ArrayList<>());
        }
        // 名字校验

        Set<String> englisNameSet = pluginDTO.getToolRequestInfo()
            .getToolsInfoList()
            .stream()
            .filter(item -> !item.getToolId().equals(toolId))
            .map(ToolInfo::getToolDisplayName)
            .collect(Collectors.toSet());

        if (pluginDTO.getToolRequestInfo().getToolsInfoList().size() > 1 && englisNameSet.contains(
            createPluginToolReq.getToolDisplayName())) {
            throw new AgentStudioException(StudioError.TOOL_EN_NAME_ALREADY_EXIST);
        }

        ToolInfo newToolInfo = new ToolInfo();

        // 提取path
        newToolInfo.setToolId(toolId);
        newToolInfo.setToolDisplayName(createPluginToolReq.getToolDisplayName());
        newToolInfo.setToolChineseName(createPluginToolReq.getToolChineseName());
        newToolInfo.setToolDesc(createPluginToolReq.getToolDesc());
        newToolInfo.setPath(
            getToolPath(pluginDTO.getToolRequestInfo().getBasicInfo(), createPluginToolReq.getRequestInfo().getUrl()));
        newToolInfo.setMethod(createPluginToolReq.getRequestInfo().getMethod().toString());
        ToolInfo editTool = pluginDTO.getToolRequestInfo()
            .getToolsInfoList()
            .stream()
            .filter(p -> Strings.CS.equals(p.getToolId(), toolId))
            .findFirst()
            .orElse(new ToolInfo());
        newToolInfo.setFunctionId(editTool.getFunctionId());

        ToolInputSchema toolInputSchema = ToolInputSchema.builder()
            .toolId(toolId)
            .inputSchema(createPluginToolReq.getInputSchema())
            .build();

        ToolOutputSchema toolOutputSchema = ToolOutputSchema.builder()
            .toolId(toolId)
            .outputSchema(createPluginToolReq.getOutputSchema())
            .build();

        ToolIntfType toolIntfType = ToolIntfType.builder()
            .toolId(toolId)
            .intfType(createPluginToolReq.getIntfType())
            .build();

        String testStatus = createPluginToolReq.getTestStatus();
        ToolTestStatus toolTestStatus = ToolTestStatus.builder()
            .toolId(toolId)
            .testStatus(TestStatus.UNKNOWN.getCode())
            .build();

        Boolean isInputList = createPluginToolReq.isIsInputList();
        Boolean isOutputList = createPluginToolReq.isIsOutputList();
        IsInputList toolIsInputList = IsInputList.builder().toolId(toolId).isList(isInputList).build();
        IsOutputList toolIsOutputList = IsOutputList.builder().toolId(toolId).isList(isOutputList).build();
        if (testStatus != null && testStatus.equals("FAILED")) {
            toolTestStatus.setTestStatus(TESTFAIL);
        } else if (testStatus != null && testStatus.equals("SUCCESS")) {
            toolTestStatus.setTestStatus(TESTSUCCESS);
        }

        if (pluginDTO.getToolRequestInfo().getToolsInfoList().size() == 1) {
            pluginDTO.getToolRequestInfo().getToolsInfoList().set(0, newToolInfo);
            pluginDTO.getToolInputSchemaList().set(0, toolInputSchema);
            pluginDTO.getToolOutputSchemaList().set(0, toolOutputSchema);
            pluginDTO.getToolIntfTypeList().set(0, toolIntfType);
            pluginDTO.getToolTestStatusList().set(0, toolTestStatus);
            pluginDTO.getIsInputList().set(0, toolIsInputList);
            pluginDTO.getIsOutputList().set(0, toolIsOutputList);
        } else {
            // 更新 ToolsInfoList
            pluginDTO.getToolRequestInfo()
                .getToolsInfoList()
                .replaceAll(toolInfo -> toolInfo.getToolId().equals(toolId) ? newToolInfo : toolInfo);

            // 更新 ToolInputSchemaList
            pluginDTO.getToolInputSchemaList()
                .replaceAll(inputSchema -> inputSchema.getToolId().equals(toolId) ? toolInputSchema : inputSchema);

            // 更新 ToolOutputSchemaList
            pluginDTO.getToolOutputSchemaList()
                .replaceAll(outputSchema -> outputSchema.getToolId().equals(toolId) ? toolOutputSchema : outputSchema);

            // 更新 ToolIntfTypeList
            pluginDTO.getToolIntfTypeList()
                .replaceAll(intfType -> intfType.getToolId().equals(toolId) ? toolIntfType : intfType);

            // 更新 ToolTestStatusList
            pluginDTO.getToolTestStatusList()
                .replaceAll(test -> test.getToolId().equals(toolId) ? toolTestStatus : test);

            // 添加元素到 IsInputList
            pluginDTO.getIsInputList().replaceAll(input -> input.getToolId().equals(toolId) ? toolIsInputList : input);

            // 添加元素到 IsInputList
            pluginDTO.getIsOutputList()
                .replaceAll(output -> output.getToolId().equals(toolId) ? toolIsOutputList : output);
        }

        PluginEntity pluginEntity = pluginBase.transformDTOtoNewEntity(pluginDTO);

        pluginBase.validateDuplicateInputSchema(pluginDTO.getToolInputSchemaList(), pluginDTO.getToolRequestInfo());

        pluginMapper.updateByPrimaryKeySelective(pluginEntity);

    }

    private void subTool(String toolId, PluginDTO pluginDTO) {

        if (pluginDTO.getToolRequestInfo().getToolsInfoList() == null) {
            pluginDTO.getToolRequestInfo().setToolsInfoList(new ArrayList<>());
        }

        if (pluginDTO.getToolRequestInfo().getToolsInfoList().size() == 1) {
            // 第一次没有toolid
            pluginDTO.getToolRequestInfo().getToolsInfoList().clear();
            pluginDTO.getToolInputSchemaList().clear();
            pluginDTO.getToolOutputSchemaList().clear();
            pluginDTO.getToolIntfTypeList().clear();
            pluginDTO.getToolTestStatusList().clear();
            pluginDTO.getIsInputList().clear();
            pluginDTO.getIsOutputList().clear();
        } else {
            pluginDTO.getToolRequestInfo().getToolsInfoList().removeIf(toolInfo -> toolInfo.getToolId().equals(toolId));
            pluginDTO.getToolInputSchemaList().removeIf(inputSchema -> inputSchema.getToolId().equals(toolId));
            pluginDTO.getToolOutputSchemaList().removeIf(outputSchema -> outputSchema.getToolId().equals(toolId));
            pluginDTO.getToolIntfTypeList().removeIf(intfType -> intfType.getToolId().equals(toolId));
            pluginDTO.getToolTestStatusList().removeIf(testStatus -> testStatus.getToolId().equals(toolId));
            pluginDTO.getIsInputList().removeIf(isInputList -> Strings.CS.equals(toolId, isInputList.getToolId()));
            pluginDTO.getIsOutputList().removeIf(isOutputList -> Strings.CS.equals(toolId, isOutputList.getToolId()));
        }
        PluginEntity pluginEntity = pluginBase.transformDTOtoNewEntity(pluginDTO);

        pluginMapper.updateByPrimaryKeySelective(pluginEntity);
    }

    public static UrlInfo parseUrl(String urlString) {

        // 处理没有显式协议的URL（默认视为http）
        if (!urlString.startsWith("http://") && !urlString.startsWith("https://")) {
            urlString = "http://" + urlString;
        }

        URL url = null;
        try {
            url = new URL(urlString);
        } catch (MalformedURLException e) {
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 提取信息
        String protocol = url.getProtocol();
        String host = url.getPort() < 0 ? url.getHost() : url.getHost() + ":" + url.getPort();
        String path = url.getPath();

        // 如果路径为空，设置为"/"
        if (path == null || path.isEmpty()) {
            path = "/";
        }

        return UrlInfo.builder()
            .host(host)
            .port(String.valueOf(url.getPort()))
            .basePath(path)
            .protocol(protocol)
            .build();
    }

    public static UrlInfo parseVariableUrl(String urlString) {
        // 如果没有显式协议，自动补上 http://
        if (!urlString.startsWith("http://") && !urlString.startsWith("https://")) {
            urlString = "http://" + urlString;
        }

        // 提取协议
        String protocol;
        int protocolEndIndex;
        if (urlString.startsWith("https://")) {
            protocol = "https";
        } else {
            protocol = "http";
        }
        protocolEndIndex = protocol.length() + 3;

        // 从协议之后开始找第一个斜杠
        int firstSlashIndex = urlString.indexOf('/', protocolEndIndex);

        String hostPart;
        String basePath;

        if (firstSlashIndex == -1) {
            // 没有斜杠，整个 URL（除去协议）都是 host，basePath 为 "/"
            hostPart = urlString.substring(protocolEndIndex);
            basePath = "/";
        } else {
            // 有斜杠，分割 host 和 basePath
            hostPart = urlString.substring(protocolEndIndex, firstSlashIndex);
            basePath = urlString.substring(firstSlashIndex);
        }

        return UrlInfo.builder().host(hostPart).basePath(basePath).protocol(protocol).build();
    }

    @NotNull
    private PluginDTO buildPluginEntity(String projectId, String workspaceId, CreatePluginToolReq body) {
        RequestInfo pluginInfo = body.getRequestInfo();

        // 构建requestInfo字段，包括BasicInfo和tool_info
        UrlInfo urlInfo = null;
        if (pluginInfo.getUrl().contains("{")) {
            urlInfo = parseVariableUrl(pluginInfo.getUrl());
        } else {
            urlInfo = parseUrl(pluginInfo.getUrl());
        }
        BasicInfo basicInfo = BasicInfo.builder()
            .host(urlInfo.getHost())
            .protocol(urlInfo.getProtocol())
            .path(urlInfo.getBasePath())
            .inputSchema(pluginInfo.getInputSchema())
            .build();

        // 适配多斜杠的问题
        adaptPluginUrlWhenCreateOrModify(basicInfo, urlInfo);

        ToolRequestInfo pluginRequest = ToolRequestInfo.builder().basicInfo(basicInfo).build();
        pluginRequest.setToolsInfoList(new ArrayList<>());
        // 工具参数信息校验
        checkUrl(pluginInfo, null);
        checkToolInfo(body.getToolDisplayName(), body.getVisibility());

        // op账号创建并且auth_required信息为true的，清空AuthInfo信息
        if (isOpTenant(projectId) && body.isAuthRequired()) {
            clearAuthInfo(body.getAuthInfo());
        } else {
            body.setAuthInfo(encryptedAuthInfo(body.getAuthInfo()));
        }
        return getPluginDTO(projectId, workspaceId, body, pluginRequest);
    }

    @NotNull
    private PluginDTO getPluginDTO(String projectId, String workspaceId, CreatePluginToolReq body,
        ToolRequestInfo pluginRequest) {
        // 普通租户创建工具类型是自定义，承载租户创建工具类型是预置，知识库工具标识在metadata中
        PluginDTO pluginEntity = new PluginDTO();

        // 如果为OP账号创建的内置插件，插件id固定，使用前缀+小写英文名；否则使用UUID
        pluginEntity.setPluginId(isOpTenant(projectId)
            ? PRESET + StringUtils.lowerCase(body.getToolDisplayName())
            : UUID.randomUUID().toString());
        pluginEntity.setTraceId(pluginEntity.getPluginId());
        pluginEntity.setProjectId(projectId);
        pluginEntity.setWorkspaceId(workspaceId);
        pluginEntity.setPluginDisplayName(body.getToolDisplayName());
        pluginEntity.setPluginChineseName(body.getToolChineseName());
        pluginEntity.setPluginDesc(body.getToolDesc());
        pluginEntity.setCallMode(body.getCallMode());
        if (body.getIcon() == null) {
            pluginEntity.setIcon(defaultIcon);
        } else {
            IconNameCheckUtils.validaIconName(body.getIcon());
            pluginEntity.setIconName(body.getIcon());
            String icon = ImageBase64Utils.getImageBase64(body.getIcon(), mgObsService);
            pluginEntity.setIcon(icon);
        }
        if (!Objects.isNull(body.getAuthInfo()) && AuthInfo.ScopeEnum.IAM.equals(body.getAuthInfo().getScope())
            && !Objects.isNull(body.getAuthInfo().getIamCredentials())) {
            body.getAuthInfo()
                .getIamCredentials()
                .put(CommonConstant.DOMAIN_ID, RequestContextUtils.getRequestUserDomainId());
        }
        pluginEntity.setAuthInfo(body.getAuthInfo());
        pluginEntity.setVisibility(body.getVisibility());
        pluginEntity.setType(pluginEntity.getType() != null ? pluginEntity.getType() : getPluginType(projectId));

        pluginEntity.setCreator(
            isOpTenant(projectId) ? CommonConstant.DEFAULT_USERNAME : RequestContextUtils.getRequestUserName());
        pluginEntity.setCreatorId(RequestContextUtils.getRequestUserId());

        // 列表初始化
        pluginEntity.setToolTestStatusList(new ArrayList<>());
        pluginEntity.setToolIntfTypeList(new ArrayList<>());
        pluginEntity.setToolInputSchemaList(new ArrayList<>());
        pluginEntity.setToolOutputSchemaList(new ArrayList<>());
        pluginEntity.setIsInputList(new ArrayList<>());
        pluginEntity.setIsOutputList(new ArrayList<>());

        pluginEntity.setToolRequestInfo(Objects.isNull(pluginRequest) ? new ToolRequestInfo() : pluginRequest);
        pluginEntity.setAuthRequired(body.isAuthRequired());
        urlCheckUtils.checkUrl(null, body.getMetadata());
        pluginEntity.setMetadata(body.getMetadata());
        pluginEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());

        return pluginEntity;
    }

    @NotNull
    private static AuthInfo getFunctionAuthInfo() {
        AuthInfo functionAuthInfo = new AuthInfo();
        functionAuthInfo.setScope(AuthInfo.ScopeEnum.USER);
        functionAuthInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        functionAuthInfo.setAuthKeys(List.of(
            new AuthKeyInfo().setSourceName(CommonConstant.X_AUTH_TOKEN).setTargetName(CommonConstant.X_AUTH_TOKEN)));
        return functionAuthInfo;
    }

    private PluginEntity ConvertPluginFromModifyBody(ModifyPluginReq body, PluginEntity oldPlugin) {
        // 构建requestInfo字段，包括BasicInfo和tool_info
        BasicInfo basicInfo = null;
        RequestInfo requestInfo = body.getRequestInfo();
        UrlInfo urlInfo = null;
        if (requestInfo.getUrl().contains("{")) {
            urlInfo = parseVariableUrl(requestInfo.getUrl());
        } else {
            urlInfo = parseUrl(requestInfo.getUrl());
        }

        basicInfo = BasicInfo.builder()
            .host(urlInfo.getHost())
            .protocol(urlInfo.getProtocol())
            .path(urlInfo.getBasePath())
            .inputSchema(requestInfo.getInputSchema())
            .build();

        // basic path若只有/,则忽略
        adaptPluginUrlWhenCreateOrModify(basicInfo, urlInfo);

        oldPlugin.setRequestInfo(oldPlugin.getRequestInfo());

        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(oldPlugin);
        ToolRequestInfo pluginRequestInfo = pluginDTO.getToolRequestInfo();
        pluginRequestInfo.setBasicInfo(basicInfo);

        // 校验输入参数是否重名
        pluginBase.validateDuplicateInputSchema(pluginDTO.getToolInputSchemaList(), pluginRequestInfo);

        // 更新插件时,兼容老版本
        PluginEntity pluginEntity = pluginBase.transformDTOtoNewEntity(pluginDTO);

        PluginEntity newEntity = new PluginEntity();
        BeanUtils.copyProperties(pluginEntity, newEntity);

        newEntity.setPluginDisplayName(body.getToolDisplayName());
        newEntity.setPluginChineseName(body.getToolChineseName());
        newEntity.setPluginDesc(body.getToolDesc());
        newEntity.setAuthInfo(body.getAuthInfo());

        if (body.isCustomizeNode() != null) {
            newEntity.setCustomizeNode(body.isCustomizeNode() ? 1 : 0);
        }
        return newEntity;
    }

    private void checkToolInfo(String toolName, String visibility) {
        // 检查visibility取值
        if (!StringUtils.isEmpty(visibility) && !Arrays.stream(VisibilityEnum.values())
            .anyMatch(item -> item.getValue().equals(visibility))) {
            log.error("Visibility value:{} is invalid.", visibility);
            throw new AgentStudioException(StudioError.INVALID_VISIBILITY, visibility);
        }

        // 新建插件的name不在黑名单中（预置插件、知识检索插件）
        if (StringUtils.isNotBlank(toolNameBlackList) && Arrays.asList(toolNameBlackList.split(","))
            .contains(toolName)) {
            log.error("Fail to create tool for duplicate tool name [{}] in black list", toolName);
            throw new AgentStudioException(StudioError.TOOL_NAME_ALREADY_EXIST);
        }
    }

    private String getPluginType(String projectId) {
        return isOpTenant(projectId) ? ToolType.INNER.type : ToolType.CUSTOM.type;
    }

    private boolean isOpTenant(String projectId) {
        return opSvcProjectId.equals(projectId);
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

    public AuthInfo encryptedAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                if (StringUtils.isBlank(authKeyInfo.getAuthKey()) || CommonConstant.ANONYMIZED_TEXT.equals(
                    authKeyInfo.getAuthKey())) {
                    return null;
                }
                authKeyInfo.setAuthKey(
                    encryptionAdapter.encrypt(authKeyInfo.getAuthKey(), RequestContextUtils.getRequestUserDomainId()));
            }
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.HIS_IAM.equals(authInfo.getScope())) {
            HisIamInfo hisIamInfo = authInfo.getHisIamInfo();
            if (hisIamInfo != null && StringUtils.isNotBlank(hisIamInfo.getIamSecret())) {
                // 如果iam_secret不为空且未被脱敏，则加密
                if (!CommonConstant.ANONYMIZED_TEXT.equals(hisIamInfo.getIamSecret())) {
                    hisIamInfo.setIamSecret(encryptionAdapter.encrypt(hisIamInfo.getIamSecret(),
                        RequestContextUtils.getRequestUserDomainId()));
                }
            }
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SGOV.equals(authInfo.getScope())) {
            HisSgov hisSgov = authInfo.getHisSgov();
            if (hisSgov != null && StringUtils.isNotBlank(hisSgov.getCredential())) {
                // 如果iam_secret不为空且未被脱敏，则加密
                if (!CommonConstant.ANONYMIZED_TEXT.equals(hisSgov.getCredential())) {
                    hisSgov.setCredential(encryptionAdapter.encrypt(hisSgov.getCredential(),
                        RequestContextUtils.getRequestUserDomainId()));
                }
            }
        }

        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.CUSTOM_IAM.equals(authInfo.getScope())) {
            PluginIAMAuthInfo customIamCredentials = authInfo.getCustomIamCredentials();

            if (StringUtils.isNotBlank(customIamCredentials.getIamPassword())) {
                if (!CommonConstant.ANONYMIZED_TEXT.equals(customIamCredentials.getIamAk())) {
                    customIamCredentials.setIamPassword(encryptionAdapter.encrypt(customIamCredentials.getIamPassword(),
                        RequestContextUtils.getRequestUserDomainId()));
                }
            } else {
                if (!CommonConstant.ANONYMIZED_TEXT.equals(customIamCredentials.getIamAk())) {
                    customIamCredentials.setIamSk(encryptionAdapter.encrypt(customIamCredentials.getIamSk(),
                        RequestContextUtils.getRequestUserDomainId()));
                }
            }
        }
        return authInfo;
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
     * 生成16位唯一ID（基于UUID截取）
     *
     * @return 16位十六进制字符串
     */
    public static String generate16BitId() {
        // 生成标准UUID并去除连接符，得到32位字符串
        String uuid = UUID.randomUUID().toString().replace("-", "");
        // 截取前16位（也可截取后16位：uuid.substring(16)）
        return uuid.substring(0, 16);
    }

    private String getToolPath(BasicInfo basicInfo, String url) {
        // 构建BasicInfo中的前缀URL字符串
        StringBuilder prefixBuilder = new StringBuilder();
        prefixBuilder.append(basicInfo.getProtocol()).append("://").append(basicInfo.getHost());

        // 如果path不为空且不以/开头，添加/
        String basicPath = basicInfo.getPath();
        if (basicPath != null && !basicPath.isEmpty()) {
            prefixBuilder.append(basicPath);
        }
        String prefixUrl = prefixBuilder.toString();

        // 检查前缀是否匹配
        if (!url.startsWith(prefixUrl)) {
            log.error("URL prefix not match, expect: {}, real: {}", prefixUrl, url);
            throw new AgentStudioException(StudioError.URL_PREFIX_NOT_MATCH, prefixUrl, url);
        }

        // 提取并返回URL中除前缀外的部分
        return url.substring(prefixUrl.length());
    }

    public void validPlugins(Set<String> pluginIds, String projectId, String workspaceId) {
        for (String pluginId : pluginIds) {
            PluginEntity pluginEntity = pluginMapper.selectByPrimaryKey(pluginId, null);

            if ((ToolType.CUSTOM.type.equals(pluginEntity.getType()) && !Strings.CS.equals(workspaceId,
                pluginEntity.getWorkspaceId()))) {
                throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION,
                    String.format("%s.", pluginId));
            }
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Plugin",
        description = "更新插件认证信息",
        resourceId = "pluginId",
        resourceName = ""
    )
    public PluginAuthUpdateRsp updatePluginAuthInfo(String projectId, String workspaceId, String pluginId,
        PluginAuthUpdateReq body) {
        log.info("operation log {}: start to update plugin auth info, pluginId: {}", projectId, pluginId);

        // 1. 查询插件实体并校验是否存在
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, projectId, workspaceId);
        if (Objects.isNull(pluginEntity)) {
            log.error("Fail to update auth info, plugin [{}] not exist under tenant [{}]", pluginId, projectId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST,
                String.format("plugin id %s not exist", pluginId));
        }

        // authkey改成非必要
        AuthInfo authInfoReq = body.getAuthInfo();
        if (authInfoReq.getAuthKeys() != null && (authInfoReq.getDomain() == null || authInfoReq.getScope() == null)) {
            throw new AgentStudioException(StudioError.PLUGIN_AUTH_KEY_DOMAIN_NOT_NULL);
        }

        // 2. 复用现有的加密逻辑，对最新的鉴权信息进行加密
        AuthInfo encryptedAuth = encryptedAuthInfo(authInfoReq);
        log.info("updatePluginAuthInfo log {}: auth info id encrypt, pluginId: {}", projectId, pluginId);

        // 3. 将加密后的鉴权信息赋予实体，准备更新数据库
        pluginEntity.setAuthInfo(encryptedAuth);
        pluginEntity.setUpdatedOn(new Date());

        PluginAuthUpdateRsp response = new PluginAuthUpdateRsp();
        response.setPluginId(pluginId);

        String versionId = pluginEntity.getLastVersionId();
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(pluginId, versionId);
        if (existVersion != null) {
            // 【已发布】：仅更新数据库中的鉴权字段，不改变当前版本号
            String releaseDslPath = obsService.uploadObsFile(pluginEntity.getPluginId(),
                pluginEntity.getPluginId() + Constants.UNDERLINE_STR + pluginEntity.getVersionId(), CommonConstant.TOOL,
                JsonUtils.toJson(pluginEntity), CommonConstant.DSL_STR);
            log.info("updatePluginAuthInfo upload obs success pluginId: {}", pluginId);
            existVersion.setDslPath(releaseDslPath);
            existVersion.setReleasedOn(new Date());
            pluginMapper.updateByPrimaryKeySelective(pluginEntity);
            releaseVersionMapper.updateDsl(existVersion);
            response.setIsNewlyPublished(false);
            response.setVersionId(pluginEntity.getLastVersionId());
            response.setMessage("Auth info updated successfully (Plugin already published, version unchanged).");
            log.info("Plugin {} is already published. Auth info updated without changing version.", pluginId);
        } else {
            throw new AgentStudioException(StudioError.RELEASE_PUBLISH_FAILED,
                "plugin publish failed! " + pluginId);
        }

        return response;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Plugin",
        description = "插件版本还原",
        resourceId = "pluginId",
        resourceName = "versionId"
    )
    public BaseResp updatePluginVersionByVersionId(String projectId, String pluginId, String versionId,
        String workspaceId) {
        log.info("operation log {}: start to update plugin version by version id", projectId);
        PluginEntity pluginEntityByVersion = pluginBase.getPluginEntityByVersion(pluginId, versionId);
        PluginDTO pluginDTO = pluginBase.transformEntityToDTO(pluginEntityByVersion);
        pluginMapper.updateByPrimaryKeySelective(pluginEntityByVersion);
        return new BaseResp().setCode(200).setMessage("success").setData(pluginDTO);
    }

    /**
     * 处理basicPath的路径拼接多斜杠的问题
     * @param basicInfo 基准信息
     * @param urlInfo url解析信息
     */
    public void adaptPluginUrlWhenCreateOrModify(BasicInfo basicInfo, UrlInfo urlInfo) {
        String basePath = urlInfo.getBasePath();
        if (basePath.endsWith("/")) {
            basePath = basePath.substring(0, basePath.length() - 1);
            basicInfo.setPath(basePath);
        }
    }

    /**
     * 工具描述国际化
     * @param toolRequestInfo 工具信息
     */
    public void adaptDescOfToolInfo(ToolRequestInfo toolRequestInfo) {
        List<ToolInfo> toolsInfoList = toolRequestInfo.getToolsInfoList();
        toolsInfoList.forEach(toolInfo -> {
            if (StringUtils.isBlank(toolInfo.getToolDescEn())) {
                toolInfo.setToolDescEn(toolInfo.getToolDesc());
            }
        });
    }

    /**
     * 插件描述国际化
     * @param pluginDTO 插件dto
     */
    public void adaptDescOfPluginInfo(PluginDTO pluginDTO) {
        if (StringUtils.isBlank(pluginDTO.getPluginDescEn())) {
            pluginDTO.setPluginDescEn(pluginDTO.getPluginDesc());
        }
    }
}

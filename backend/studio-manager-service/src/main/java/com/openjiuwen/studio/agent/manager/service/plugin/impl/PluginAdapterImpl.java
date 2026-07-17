/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin.impl;

import static com.openjiuwen.studio.agent.common.enums.NodeType.PLUGIN;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginRequest;
import com.openjiuwen.studio.agent.manager.entity.plugin.RequestResult;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.OkHttpUtils;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import inet.ipaddr.IPAddressString;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.parser.OpenAPIV3Parser;
import io.swagger.v3.parser.core.models.SwaggerParseResult;
import jodd.util.StringUtil;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.commons.lang3.math.NumberUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.UnknownHostException;
import java.time.LocalDate;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PluginAdapterImpl implements IPlugin {

    /**
     * 接口测试OBS临时目录
     */
    public static final String TOOL_TEST_OBS_PATH = "temp/tools/openapi";

    /**
     * 加密的字段，例如apikey鉴权的秘钥，返回前端******
     */
    public static final String ENCRYPTED_VALUE = "******";

    /**
     * 预置插件前缀
     */
    private static final String PRESET = "preset_";

    private static final String FUNCTION = "functions";

    @Value("${asset.publish.review_account:domainid#projectid#userId}")
    private String reviewAccountSet;

    @Value("${publish_account:domainid}")
    private String publishAccount;

    @Autowired
    private OkHttpUtils okHttpUtils;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    /**
     * 合规的url正则
     */
    private static final String VALID_URL = "^(http|https)://" + "[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*" + "(:\\d+)?"
            + "(/[a-zA-Z0-9_\\-./#?=&%]*)?$";

    private static final Pattern VALID_URL_PATTERN = Pattern.compile(VALID_URL);

    /**
     * 用于提取文件名的正则表达式
     */
    private static final Pattern FILE_NAME_PATTERN = Pattern.compile(".+/([^/?]+)(\\?.+)?$");

    @Value("${workflow.connector_config_host_blacklist}")
    private String connectorConfigHostBlacklist;

    @Value("#{'${workflow.connector_config_host_whitelist}'.split(',')}")
    private Set<String> connectorConfigHostWhitelist;

    @Value("${tool.url.enable-check}")
    private boolean enableUrlCheck;

    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private IPluginBase pluginBase;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Value("${asset.free.trial-quota-limit:10}")
    private int pluginMaxFreeTrialTimes;

    private static final String PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT
            = "agent.manager.asset.plugin.free.trial.usage.quota.asset_%s.month_%d.domain_%s";

    @Autowired
    private RedisClient redisClient;

    @Override
    public List<ToolReference> getToolReferences(String projectId, String workspaceId, List<String> pluginIds) {
        log.info("start to get tool References!");
        Map<String, List<String>> tools = convertToolIds2PluginToolMap(pluginIds);
        List<String> pluginIsSharedIds = filterIdIsShared(tools.keySet().stream().toList());
        List<String> pluginCurUser = filterPluginIds(tools.keySet().stream().toList(), pluginIsSharedIds);
        List<PluginEntity> input = new ArrayList<>();
        List<PluginEntity> pluginEntities = pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(projectId,
            workspaceId, pluginCurUser, null);
        List<PluginEntity> pluginEntitiesIsShared = pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(
            projectId, null, pluginIsSharedIds, null);
        if (CollectionUtils.isNotEmpty(pluginEntities)) {
            input.addAll(pluginEntities);
        }
        if (CollectionUtils.isNotEmpty(pluginEntitiesIsShared)) {
            input.addAll(pluginEntitiesIsShared);
        }
        List<ToolReference> result = new ArrayList<>();
        for (PluginEntity plugin : input) {
            if (isNewTool(plugin)) {
                List<ToolReference> toolReferences = buildTools(plugin, tools.get(plugin.getPluginId()), workspaceId);
                result.addAll(toolReferences);
            } else {
                PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(
                    plugin.getPluginId(), null, workspaceId);
                ToolReference toolReference = new ToolReference();
                toolReference.setToolId(plugin.getPluginId() + "#0");
                toolReference.setPluginDisplayName(plugin.getPluginDisplayName());
                toolReference.setPluginChineseName(plugin.getPluginChineseName());
                toolReference.setToolDisplayName(plugin.getPluginDisplayName());
                toolReference.setToolChineseName(plugin.getPluginChineseName());
                if (ToolType.INNER.type.equals(plugin.getType())) {
                    toolReference.setToolChineseName(plugin.getPluginDisplayName());
                }
                toolReference.setToolIcon(plugin.getIcon());
                toolReference.setDesc(plugin.getPluginDesc());
                toolReference.setCredentialStatus(pluginEntity.getCredentialStatus());
                toolReference.setAuthInfo(anonymizeAuthInfo(pluginEntity.getAuthInfo()));
                setupFreeTrialQuota(plugin, toolReference, pluginMaxFreeTrialTimes);
                toolReference.setIsFree(plugin.getIsFree());
                if (StringUtils.isNotEmpty(plugin.getLastVersionId())) {
                    ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(plugin.getPluginId(),
                        plugin.getLastVersionId());
                    if (ObjectUtils.isNotEmpty(releaseVersion)) {
                        toolReference.setLastVersionId(plugin.getLastVersionId());
                        toolReference.setLastVersionName(releaseVersion.getVersionName());
                    }
                }
                result.add(toolReference);
            }
        }
        return result;
    }

    private String getPluginFreeTrialUsageQuotaKey(String domainId, String pluginId) {
        return String.format(Locale.ROOT, PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT, pluginId,
                LocalDate.now().getMonthValue(), domainId);
    }

    private List<String> filterIdIsShared(List<String> tools) {
        List<ShareResourceEntity> shareScopes = shareInnerService.getOriginSharedInfoByResourceId(tools);
        List<String> result = shareScopes.stream().map(ShareResourceEntity::getResourceId).toList();
        log.info(">>>filterIdIsShared id {}", result);
        return result;
    }

    private List<String> filterPluginIds(List<String> originIds, List<String> deleteIds) {
        // 创建一个新的列表用于存储结果
        List<String> result = new ArrayList<>();

        // 过滤 pluginIds
        for (String id : originIds) {
            if (!deleteIds.contains(id)) {
                result.add(id);
            }
        }
        return result;
    }

    private List<ToolReference> buildTools(PluginEntity plugin, List<String> targetTools, String workspaceId) {
        List<ToolReference> result = new ArrayList<>();
        if (ObjectUtils.isEmpty(plugin.getRequestInfo())) {
            return result;
        }

        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(plugin.getPluginId(), null,
            workspaceId);
        AuthInfo authInfo = anonymizeAuthInfo(pluginEntity.getAuthInfo());
        JSONObject jsonObject = JSON.parseObject(plugin.getRequestInfo());
        List<ToolInfo> toolsInfos = jsonObject.getList("tool_info", ToolInfo.class);
        for (ToolInfo toolInfo : toolsInfos) {
            if (targetTools.contains(toolInfo.getToolId())) {
                ToolReference toolReference = new ToolReference();
                toolReference.setToolId(plugin.getPluginId() + "#" + toolInfo.getToolId());
                toolReference.setPluginDisplayName(plugin.getPluginDisplayName());
                toolReference.setPluginChineseName(plugin.getPluginChineseName());
                toolReference.setToolDisplayName(toolInfo.getToolDisplayName());
                toolReference.setToolChineseName(toolInfo.getToolChineseName());
                toolReference.setToolIcon(plugin.getIcon());
                toolReference.setDesc(toolInfo.getToolDesc());
                toolReference.setCredentialStatus(pluginEntity.getCredentialStatus());
                toolReference.setAuthInfo(authInfo);
                toolReference.setMetadata(plugin.getMetadata());
                toolReference.setIsFree(plugin.getIsFree());
                setupFreeTrialQuota(plugin, toolReference, pluginMaxFreeTrialTimes);
                if (StringUtils.isNotEmpty(plugin.getLastVersionId())) {
                    ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(plugin.getPluginId(),
                        plugin.getLastVersionId());
                    if (ObjectUtils.isNotEmpty(releaseVersion)) {
                        toolReference.setLastVersionId(plugin.getLastVersionId());
                        toolReference.setLastVersionName(releaseVersion.getVersionName());
                    }
                }
                result.add(toolReference);
            }
        }
        return result;
    }

    /**
     * 设置插件的免费试用额度（仅适用于内置免费插件）
     *
     * @param plugin               插件信息（必须包含 type 和 isFree 字段）
     * @param toolReference        工具引用对象，用于设置使用次数和上限
     * @param pluginMaxFreeTrialTimes 最大免费试用次数
     */
    public void setupFreeTrialQuota(PluginEntity plugin, ToolReference toolReference,
                                           int pluginMaxFreeTrialTimes) {
        // 内置免费额度插件
        if (ToolType.INNER.type.equals(plugin.getType()) && plugin.getIsFree() != null && plugin.getIsFree() == 1) {
            toolReference.setLimit(pluginMaxFreeTrialTimes);
            try {
                String domainId = RequestContextUtils.getRequestUserDomainId();
                String pluginFreeTrialUsageRecords =
                        redisClient.get(getPluginFreeTrialUsageQuotaKey(domainId, plugin.getPluginId()));

                if (StringUtils.isBlank(pluginFreeTrialUsageRecords)) {
                    log.info("None plugin free trial quota record stored, return zero as usage quota. " +
                            "Domain: {}, plugin: {}.", domainId, plugin.getPluginId());
                    toolReference.setUsage(0);
                }
                toolReference.setUsage(NumberUtils.toInt(pluginFreeTrialUsageRecords));
            } catch (Exception e) {
                throw new AgentStudioException(StudioError.PLUGIN_FREE_TRIAL_USAGE_QUOTA_ERROR);
            }
        }
    }


    @Override
    public boolean isNewTool(PluginEntity pluginEntity) {
        if (pluginEntity == null) {
            return false; // 或抛出异常，视业务而定
        }
        return pluginEntity.getRequestInfo().contains("basic_info");
    }

    /**
     * @param pluginEntity 插件对象
     * @return 新插件的resourceid 使用 插件id与工具id `#` 相连
     */
    @Override
    public List<String> buildResourceId(PluginEntity pluginEntity) {
        JSONObject jsonObject = JSON.parseObject(pluginEntity.getRequestInfo());
        List<ToolInfo> toolsInfo = jsonObject.getList("tool_info", ToolInfo.class);
        return toolsInfo.stream().map(toolInfo -> pluginEntity.getPluginId() + "#" + toolInfo.getToolId()).toList();
    }

    /**
     * ir转换专用
     *
     * @param id id
     * @param projectId projectId
     * @param opProjectId opProjectId
     * @param versionId versionId
     * @return ir中的插件
     */
    @Override
    public ToolEntity getToolEntity(String id, String projectId, String opProjectId, String versionId) {
        ToolEntity toolEntity;
        if (StringUtils.isNotEmpty(versionId)) {
            toolEntity = pluginBase.getToolEntityByVersion(id, versionId);
            toolEntity.setVersionId(versionId);
        } else {
            String[] ids = id.split("#");
            String pluginId = ids[0]; // 获取 pluginId
            // 确保 toolId 存在
            String toolId = ids.length > 1 ? ids[1] : "0"; // 如果存在 toolId, 否则为 null
            toolEntity = pluginBase.buildToolByPlugin(projectId, null, pluginId, toolId);
        }

        return toolEntity;
    }

    @Override
    public void validTools(String projectId, String workspaceId, List<String> toolIds) {
        Map<String, List<String>> toolMap = convertToolIds2PluginToolMap(toolIds);
        List<PluginEntity> toolEntities = pluginMapper.selectByIds(toolMap.keySet().stream().toList());
        if (CollectionUtils.isEmpty(toolEntities)) {
            throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION, String.join(",", toolIds));
        }

        // 增加共享判断，如果插件被共享到当前空间,则可以使用
        List<String> canUseIds = shareInnerService.getShareScopeByWorkspaceAndId(toolMap.keySet().stream().toList(),
            workspaceId).stream().map(ShareScopeEntity::getResourceId).toList();
        List<String> cannotUseIds = toolEntities.stream()
            .filter(tool -> "custom".equals(tool.getType()) && (!Strings.CS.equals(projectId, tool.getProjectId())
                || !Strings.CS.equals(workspaceId, tool.getWorkspaceId())))
            .map(PluginEntity::getPluginId)
            .toList();

        if (!CollectionUtils.isEmpty(canUseIds)) {
            log.info(">>>validTools {} was been shared.", canUseIds);
            return;
        }

        if (!CollectionUtils.isEmpty(cannotUseIds)) {
            throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION,
                String.join(",", cannotUseIds));
        }
    }

    @Override
    public void updateOldTool(String projectId, String versionId, String toolId) {
        // 更新最新版本号
        PluginEntity oldTool = pluginMapper.selectByPrimaryKey(toolId, projectId);
        String oldVersionId = oldTool.getLastVersionId();
        if (StringUtils.isEmpty(oldVersionId) || Long.parseLong(versionId) > Long.parseLong(oldVersionId)) {
            oldTool.setLastVersionId(versionId);
            pluginMapper.updateByPrimaryKeySelective(oldTool);
        }
    }

    @Override
    public void insertByTool(ToolEntity tool) {
        handleAdapterToolId(tool);
        pluginMapper.insert(pluginBase.transformTool2Plugin(tool));
    }

    @Override
    public void updateByOldTool(ToolEntity tool) {
        handleAdapterToolId(tool);
        pluginMapper.updateByPrimaryKeySelective(pluginBase.transformTool2Plugin(tool));
    }

    public void handleAdapterToolId(ToolEntity tool) {
        String[] ids = tool.getToolId().split("#");
        String pluginId = ids[0]; // 获取 pluginId
        tool.setToolId(pluginId);
    }

    @Override
    public ReleaseVersion releaseToolVersionHandler(String toolId, String versionId, String versionName,
        String versionNote) {
        PluginEntity toolEntity = pluginMapper.selectByPrimaryKey(toolId, null);
        ReleaseVersion releaseVersion = new ReleaseVersion();
        toolId = toolEntity.getPluginId();
        releaseVersion.setVersionId(
            StringUtils.isBlank(versionId) ? String.valueOf(System.currentTimeMillis()) : versionId);

        // 发布到OBS
        toolEntity.setLastVersionId(null);
        String releaseDslPath = obsService.uploadObsFile(toolId,
            toolId + Constants.UNDERLINE_STR + releaseVersion.getVersionId(), CommonConstant.TOOL,
            JsonUtils.toJson(toolEntity), CommonConstant.DSL_STR);
        releaseVersion.setDslPath(releaseDslPath);

        // 新版本insert t_release_version
        toolEntity.setPublished(1);
        pluginMapper.updateByPrimaryKeySelective(toolEntity);
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setReleasedOn(new Date());

        releaseVersion.setVersionName(versionName);
        releaseVersion.setVersionNote(versionNote);

        releaseVersion.setAppType(CommonConstant.TOOL_TYPE);
        releaseVersion.setStatus(CommonConstant.NORMAL);

        releaseVersion.setAppId(toolEntity.getPluginId());

        releaseVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersion.setCreatorId(RequestContextUtils.getRequestUserId());
        return releaseVersion;
    }

    @Override
    public void handleToolWithoutToolId(WorkflowExportEntity workflowExportEntity) {
        // 从工作流DSL文件中获取其nodes
        WorkflowVO dsl = workflowExportEntity.getDsl();
        List<WorkflowNodeVO> nodes = dsl.getNodes();

        for (WorkflowNodeVO node : nodes) {
            NodeType nodeType = NodeType.fromType(node.getType());
            if (nodeType == null) {
                log.error("unsupported node type {}", node.getType());
                throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
            }
            if (nodeType.equals(PLUGIN)) {
                Map<String, Object> configs = node.getConfigs();

                String tooId = getToolIdFromPlugin(String.valueOf(configs.get("id")));
                if (StringUtils.isNotEmpty(tooId)) {
                    configs.put("tool_id", tooId);
                }
            }
        }
    }

    @Override
    public String getToolIdFromPlugin(String id) {
        PluginEntity plugins = pluginMapper.selectByPrimaryKey(id,null);
        if (ObjectUtils.isEmpty(plugins)) {
            return StringUtils.EMPTY;
        }
        ToolRequestInfo toolRequestInfo;
        String requestInfo = plugins.getRequestInfo();
        if (isNewTool(plugins)) {
            try {
                JsonNode requestInfojsonNode = JsonUtils.JSON_MAPPER.readTree(
                    ObjectUtils.isEmpty(requestInfo) ? "{}" : requestInfo);

                toolRequestInfo = JsonUtils.JSON_MAPPER.treeToValue(requestInfojsonNode, ToolRequestInfo.class);

            } catch (JsonProcessingException e) {
                log.error("Failed to parse requestInfo to ToolInfo {}", e.getMessage());
                throw new AgentStudioException(StudioError.PARSE_REQUEST_TO_TOOL_FAILED);
            }
            List<ToolInfo> tools = toolRequestInfo.getToolsInfoList();
            if (tools.size() == 1) {
                return tools.get(0).getToolId();
            }
            return StringUtils.EMPTY;
        } else {
            return "0";
        }
    }

    @Override
    public RunToolResponseBody runTool(String projectId, RunToolRequestBody body) {
        // 插件调测
        log.info("[runTool] operation log, start to run tool");
        String toolId = body.getToolObsKey();
        String pluginId = toolId.split("#")[0];
        body.setParameter(processNestedStructure(body.getParameter()));
        log.info("[runTool] start to run, pluginId {}, toolId {} ", pluginId, toolId);
        JSONObject requestBody = JSON.parseObject(body.getParameter());
        log.info("[runTool] get requestBody {}", requestBody);

        // 下载OBS文件
        String objectKey = String.format("%s/%s.json", TOOL_TEST_OBS_PATH, toolId);
        String openapiJson = obsService.downloadObsFile(objectKey);
        log.info("[runTool] download openapi json success, start to parse file");

        // 解析openapi文件
        SwaggerParseResult parseResult = new OpenAPIV3Parser().readContents(openapiJson);
        // 检查解析错误，当前OBS路径上的openapi为管理面生成，后续解析过程不做强非空校验；若改为读取用户上传，需要进行强校验
        if (parseResult.getMessages() != null) {
            parseResult.getMessages().forEach(s -> log.warn("[runTool] parse open api error message, msg={}", s));
        }
        OpenAPI openAPI = parseResult.getOpenAPI();

        // 获取第一个path
        Optional<PathItem> optionalPathItem = openAPI.getPaths().values().stream().findFirst();
        if (optionalPathItem.isEmpty()) {
            log.error("[runTool] open api path is empty");
            throw new AgentStudioException(StudioError.OPEN_API_PARSE_FAILED, "open api path is empty");
        }

        // 解析Method
        Operation operation;
        OkHttpUtils.Method method;
        if (optionalPathItem.get().getPost() != null) {
            operation = optionalPathItem.get().getPost();
            method = OkHttpUtils.Method.POST;
        } else if (optionalPathItem.get().getGet() != null) {
            operation = optionalPathItem.get().getGet();
            method = OkHttpUtils.Method.GET;
        } else {
            log.error("[runTool] method is supported.");
            throw new AgentStudioException(StudioError.OPEN_API_PARSE_FAILED);
        }

        // 解析Parameters
        Map<String, String> urlParamsMap = new HashMap<>();
        Map<String, String> pathParams = new HashMap<>();
        Map<String, String> headers = new HashMap<>();
        parseParams(operation, requestBody, urlParamsMap, headers, pathParams);
        log.info("[runTool] pathParams parse to {}", pathParams);

        // 构造鉴权信息，用于前端展示的信息返回ENCRYPTED_VALUE
        Map<String, String> urlParamsEncrypted = new HashMap<>();
        urlParamsEncrypted.putAll(urlParamsMap);

        Map<String, String> headersEncrypted = new HashMap<>(headers);
        buildEncryptParams(projectId, openAPI, urlParamsMap, urlParamsEncrypted, headers, headersEncrypted);

        // 构造请求url
        String url = operation.getServers().get(0).getUrl();

        // 替换url占位符
        log.info("[runTool] before url replace: {}", url);
        for (Map.Entry<String, String> entry : pathParams.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();
            url = url.replaceAll("\\{" + key + "\\}", Matcher.quoteReplacement(value));
        }
        log.info("[runTool] after url replace: {}", url);

        // 如果是预置插件就不做黑名单网段IP校验
        log.info("[runTool] plugin is preset ? {}", pluginId.startsWith(PRESET));
        log.info("[runTool] plugin in whitelist ? {}", connectorConfigHostWhitelist.contains(pluginId));

        if (!pluginId.startsWith(PRESET) && !url.contains(FUNCTION) && !connectorConfigHostWhitelist.contains(
                pluginId)) {
            checkSwaggerUrlValid(url, connectorConfigHostBlacklist);
        }

        urlCheckUtils.checkUrl(projectId, url);
        String urlShown = url;
        if (MapUtils.isNotEmpty(urlParamsMap)) {
            StringBuilder sb = new StringBuilder(urlShown);
            sb.append("?");
            urlParamsEncrypted.forEach((k, v) -> {
                sb.append(String.format("%s=%s&", k, v));
            });
            urlShown = sb.toString().substring(0, sb.toString().length() - 1);
        }
        // 发送请求
        log.info("[runTool] open api file parse success, start to make request {}", urlShown);

        // 构造请求体
        String requestBodyJson;
        if (operation.getRequestBody() != null && Boolean.parseBoolean(
                getExtensionValue(operation.getRequestBody().getExtensions(), Constant.OpenAPI.X_ARRAY_ENCAPSULATION))) {
            // 外层封装为数组，原始接口的返回在测试接口时不再解封
            JSONArray jsonArray = new JSONArray();
            jsonArray.add(requestBody);
            requestBodyJson = JSON.toJSONString(jsonArray);
        } else {
            requestBodyJson = JSON.toJSONString(requestBody);
        }

        RequestResult requestResult;
        // 区分json和form-data
        log.info("[runTool] Handling {} request.", headers.get(Constant.CONTENT_TYPE));
        if (StringUtil.equals(headers.get(Constant.CONTENT_TYPE), Constant.MULTIPART_FORM_DATA)) {
            Map<String, String> formParams = new HashMap<>();
            Map<String, MultipartFile> fileParams = new HashMap<>();
            // 下载url数据
            for (String key : requestBody.keySet()) {
                String value = requestBody.getString(key);
                MultipartFile file = downloadFileAsMultipartFile(value);
                if(file != null) {
                    fileParams.put(key, file);
                } else {
                    formParams.put(key, value);
                }
            }
            requestResult = okHttpUtils.callFormData(url, method, headers, urlParamsMap, formParams, fileParams);
        } else {
            requestResult = okHttpUtils.call(url, method, headers, urlParamsMap, requestBodyJson);
        }
        log.info("[runTool] call tool finished, return code {}", requestResult.getCode());

        // 构造工具测试响应结果
        return new RunToolResponseBody().setRawRequestUrl(urlShown)
                .setRawRequestHeaders(headersEncrypted)
                .setRawRequestBody(requestBodyJson)
                .setRawResponse(requestResult.getResponse())
                .setRawResponseCode(requestResult.getCode())
                // 逻辑失败有两种情况，一种为返回非200，一种为接口异常；当前工具测试第二种情况算失败
                .setSuccess(StringUtils.isEmpty(requestResult.getExceptionMessage()))
                .setErrorMessage(requestResult.getExceptionMessage());
    }

    @Override
    public void updateName(ToolEntity tool) {
        pluginMapper.updateNameByPrimaryKey(tool.getToolId(), tool.getToolChineseName(), tool.getToolDisplayName());
    }

    public String getPluginId(String toolId) {
        String[] ids = toolId.split("#");
        // 获取 pluginId
        return ids[0];
    }

    @Override
    public void handleToolReleaseVersionId(WorkflowExportEntity workflowExportEntity) {
        // 从工作流DSL文件中获取其nodes
        WorkflowVO dsl = workflowExportEntity.getDsl();
        List<WorkflowNodeVO> nodes = dsl.getNodes();

        for (WorkflowNodeVO node : nodes) {
            NodeType nodeType = NodeType.fromType(node.getType());
            if (nodeType == null) {
                log.error("unsupported node type {}", node.getType());
                throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
            }
            if (nodeType.equals(PLUGIN)) {
                Map<String, Object> configs = node.getConfigs();
                if (configs != null && configs.containsKey("version_id") && configs.containsKey("id")) {
                    String toolId = (String) configs.get("id");
                    PluginEntity toolEntity = pluginMapper.selectByPrimaryKey(toolId, null);
                    if (toolEntity != null) {
                        configs.put("version_id", toolEntity.getLastVersionId());
                    }
                }
            }
        }
    }

    @Override
    public List<PluginEntity> getPlugin(String projectId, String workspaceId, List<String> pluginIds) {
        List<PluginEntity> result = pluginMapper.selectByPrimaryIdAndPluginIdsWithSearchCriteria(projectId, workspaceId,
            pluginIds, null);
        if (CollectionUtils.isNotEmpty(result)) {
            return result;
        }
        // 共享的插件，校验插件是否被共享
        List<String> originWorkspaceId = shareInnerService.getOriginSharedInfoByResourceId(pluginIds)
            .stream()
            .map(ShareResourceEntity::getWorkspaceId)
            .toList();
        result = pluginMapper.selectByPrimaryIdAndPluginIdsWithSearchCriteria(projectId, null, pluginIds, null);
        return result.stream().filter(plugin -> originWorkspaceId.contains(plugin.getWorkspaceId())).toList();

    }

    @Override
    public PluginEntity getPluginByTraceId(String workspaceId, String traceId) {
        List<PluginEntity> pluginEntities = pluginMapper.selectByTraceIdAndWorkspaceId(null, workspaceId, traceId);
        return pluginEntities.stream().findFirst().orElse(null);
    }

    private Map<String, List<String>> convertToolIds2PluginToolMap(List<String> toolIds) {
        Map<String, List<String>> toolMap = new HashMap<>();
        for (String item : toolIds) {
            String[] parts = item.split("#");
            if (parts.length == 2) {
                String key = parts[0];
                String value = parts[1];

                // 如果键不存在，则初始化列表
                toolMap.computeIfAbsent(key, k -> new ArrayList<>()).add(value);
            } else {
                toolMap.computeIfAbsent(parts[0], k -> new ArrayList<>()).add("0");
            }
        }
        return toolMap;
    }

    @Override
    public ToolEntity getOldToolEntity(String toolId, String projectId, String opProjectId, String versionId) {
        ToolEntity toolEntity;
        if (StringUtils.isNotEmpty(versionId)) {
            // 携带versionId，从OBS读取
            toolEntity = pluginBase.getToolEntityByVersion(toolId, versionId);

        } else {
            // 兼容旧工具，未保存OBS，仍然从数据库读取
            toolEntity = pluginBase.buildToolByPlugin(projectId, null, toolId, "0");
        }
        return toolEntity;
    }

    private boolean isNewTool(String id) {
        return id.contains("#");
    }

    // 对于服务级鉴权，需要把authKey值设置为null，0625修改为"******"与其他服务统一
    public AuthInfo anonymizeAuthInfo(AuthInfo authInfo) {
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            authInfo.getAuthKeys().forEach(authKeyInfo -> authKeyInfo.setAuthKey(maskKey(authKeyInfo.getAuthKey())));
        }
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.HIS_IAM.equals(authInfo.getScope())) {
            authInfo.getHisIamInfo().setIamSecret(maskKey(authInfo.getHisIamInfo().getIamSecret()));
        }
        if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SGOV.equals(authInfo.getScope())) {
            authInfo.getHisSgov().setCredential(maskKey(authInfo.getHisSgov().getCredential()));
        }
        return authInfo;
    }

    private String maskKey(String key) {
        if (StringUtils.isBlank(key)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }
        String decryptedKey = encryptionAdapter.decrypt(key);
        if (StringUtils.isBlank(decryptedKey)) {
            return CommonConstant.ANONYMIZED_TEXT;
        }
        if (key.length() == 1) {
            return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1);
        }
        return decryptedKey.charAt(0) + CommonConstant.ANONYMIZED_TEXT.substring(1,
            CommonConstant.ANONYMIZED_TEXT.length() - 1) + decryptedKey.charAt(decryptedKey.length() - 1);
    }

    /**
     * 从指定URL下载文件并转换为MultipartFile对象
     *
     * @param fileUrl 文件下载地址
     * @return MultipartFile对象
     */
    @SneakyThrows
    public MultipartFile downloadFileAsMultipartFile(String fileUrl) {
        log.info("downloadFileAsMultipartFile: {}", fileUrl);

        if (!VALID_URL_PATTERN.matcher(fileUrl).matches()) {
            return null;
        }

        long startTime = System.currentTimeMillis();
        InputStream inputStream = obsService.getByUrl(fileUrl);
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        try {
            // 将输入流读取到字节数组
            byte[] buffer = new byte[1024];
            int length;
            while ((length = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, length);
            }
            byte[] fileBytes = outputStream.toByteArray();

            // 创建MultipartFile对象
            String fileName = extractFileName(fileUrl); // 从 URL 中提取文件名
            log.info("downloadFileAsMultipartFile:{}, cost: {} ms", fileUrl, System.currentTimeMillis() - startTime);
            return new MockMultipartFile(fileName, fileName, "application/octet-stream", fileBytes);
        } finally {
            closeResources(inputStream, outputStream);
        }
    }

    private void parseParams(Operation operation, JSONObject requestBody, Map<String, String> urlParams,
                             Map<String, String> headers, Map<String, String> pathParams) {
        for (Parameter parameter : operation.getParameters()) {
            String parameterName = parameter.getName();

            if (Constant.OpenAPI.IN_QUERY.equals(parameter.getIn()) && requestBody.containsKey(parameter.getName())) {
                // 提取urlParameter
                String queryValue = StringUtils.defaultString(requestBody.getString(parameterName));
                // 将queryParam从请求体中移除
                requestBody.remove(parameterName);
                urlParams.put(parameterName, queryValue);
            } else if (Constant.OpenAPI.IN_HEADER.equals(parameter.getIn())) {
                // 提取headerParameter，先从自定义字段获取header的值（已加密）
                String headerValue = getExtensionValue(parameter.getExtensions(), Constant.OpenAPI.X_VALUE);
                if (StringUtils.isNotEmpty(headerValue)) {
                    headers.put(parameterName, CryptoUtils.decrypt(headerValue));
                    continue;
                }
                // 如果取不到，则从请求体中获取
                headerValue = requestBody.getString(parameterName);
                if (StringUtils.isNotEmpty(headerValue)) {
                    headers.put(parameterName, headerValue);
                    // 将headerParam从请求体中移除
                    requestBody.remove(parameterName);
                }
            } else if (Constant.OpenAPI.IN_PATH.equals(parameter.getIn())) {
                // 提取pathParameter
                if (operation.getServers().get(0).getUrl().contains("{" + parameterName + "}")
                        && StringUtils.isNotEmpty(requestBody.getString(parameterName))) {
                    pathParams.put(parameterName, requestBody.getString(parameterName));
                }
                // 将pathParam从请求体中移除
                requestBody.remove(parameterName);
            }
        }
    }

    private String getExtensionValue(Map<String, Object> extensions, String key) {
        if (extensions == null || extensions.isEmpty()) {
            return "";
        }
        return extensions.get(key).toString();
    }

    /**
     * 从URL中提取文件名
     *
     * @param fileUrl 文件URL
     * @return 文件名
     */
    public static String extractFileName(String fileUrl) {
        Matcher matcher = FILE_NAME_PATTERN.matcher(fileUrl);
        if (matcher.find()) {
            return matcher.group(1); // 返回第一个捕获组的内容
        }
        return ""; // 如果没有匹配到，返回空字符串
    }

    /**
     * 关闭资源
     */
    private void closeResources(InputStream inputStream, OutputStream outputStream) {
        if (inputStream != null) {
            try {
                inputStream.close();
            } catch (IOException e) {
                log.warn("Failed to close the input stream", e);
            }
        }

        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                log.warn("Failed to close the output stream", e);
            }
        }
    }

    public String processNestedStructure(String rawJson) {
        log.info("Start processing JSON: {}", rawJson);

        JSONObject root = JSON.parseObject(rawJson);
        log.info("Parsed JSON: {}", root.toJSONString());

        // 遍历 JSON 中的所有字段
        for (String key : root.keySet()) {
            Object value = root.get(key);

            // 如果值是数组
            if (value instanceof JSONArray) {
                JSONArray outerArray = (JSONArray) value;

                // 遍历数组中的每个对象
                for (Object item : outerArray) {
                    if (item instanceof JSONObject) {
                        JSONObject innerObj = (JSONObject) item;

                        // 如果对象中也有同名字段
                        if (innerObj.containsKey(key)) {
                            Object innerValue = innerObj.get(key);

                            // 替换最外层的字段值为内层的值
                            root.put(key, innerValue);
                            log.info("Replaced outer field '{}' with inner value", key);
                            break;
                        }
                    }
                }
            }

            // 如果值是对象
            else if (value instanceof JSONObject) {
                JSONObject innerObj = (JSONObject) value;

                // 如果对象中也有同名字段
                if (innerObj.containsKey(key)) {
                    Object innerValue = innerObj.get(key);

                    // 替换最外层的字段值为内层的值
                    root.put(key, innerValue);
                    log.info("Replaced outer field '{}' with inner value", key);
                }
            }
        }

        String newJson = root.toJSONString();
        log.info("Processed JSON result: {}", newJson);

        return newJson;
    }

    public void buildEncryptParams(String projectId, OpenAPI openAPI, Map<String, String> urlParams,
                                   Map<String, String> urlParamsEncrypted, Map<String, String> headers, Map<String, String> headersEncrypted) {
        log.info("Start to decrypt the parameters of openapi;");
        if (openAPI.getComponents() == null) {
            return;
        }
        for (Map.Entry<String, SecurityScheme> entry : openAPI.getComponents().getSecuritySchemes().entrySet()) {
            if (Constant.OpenAPI.API_KEY.equals(entry.getKey())) {
                SecurityScheme securityScheme = entry.getValue();
                if (StringUtils.isBlank(getExtensionValue(securityScheme.getExtensions(), Constant.OpenAPI.X_VALUE))) {
                    log.info("The AuthInfo of the OP account has been cleared; skipping SCC decryption.");
                    return;
                }
                String value = CryptoUtils.decrypt(
                        getExtensionValue(securityScheme.getExtensions(), Constant.OpenAPI.X_VALUE));
                switch (securityScheme.getIn()) {
                    case QUERY -> {
                        urlParams.put(securityScheme.getName(), value);
                        urlParamsEncrypted.put(securityScheme.getName(), ENCRYPTED_VALUE);
                    }
                    case HEADER -> {
                        headers.put(securityScheme.getName(), value);
                        headersEncrypted.put(securityScheme.getName(), ENCRYPTED_VALUE);
                    }
                }
            }
        }
    }

    /**
     * host 合法性检查
     *
     * @param swaggerUrl 调用url
     * @param hostBlackList 连接器host黑名单
     */
    public void checkSwaggerUrlValid(String swaggerUrl, String hostBlackList) {
        log.info("Start: check url {} from black list.", swaggerUrl);
        if (hostBlackList.isEmpty()) {
            return;
        }
        Set<String> connectorHostBlackList = Arrays.stream(hostBlackList.split(","))
                .map(String::trim)
                .collect(Collectors.toSet());
        if (!enableUrlCheck) {
            log.info("not check from black list");
            return;
        }
        try {
            URL url = new URL(swaggerUrl);
            String host = url.getHost();
            checkHostValid(host, connectorHostBlackList);
            try {
                InetAddress[] addresses = InetAddress.getAllByName(host);
                for (InetAddress address : addresses) {
                    checkHostValid(address.getHostAddress(), connectorHostBlackList);
                }
            } catch (UnknownHostException e) {
                // 不做控制，运行态DNS一样，有问题会调不通，没有影响
                log.warn("swagger base url is Unknown Host: {}", host);
            }
        } catch (MalformedURLException e) {
            throw new AgentStudioException(StudioError.INVALID_URL);
        } catch (Exception e) {
            // 捕获其他异常，防止程序崩溃
            log.error("Error while checking swagger URL: {}", swaggerUrl, e);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        log.info("End: check url from black list.");
    }

    /**
     * host 合法性检查
     *
     * @param host host
     * @param connectorHostBlackList 连接器host黑名单
     */
    public void checkHostValid(String host, Set<String> connectorHostBlackList) {
        log.info("Start: check host {} from black list.", host);

        // 判断host是否在黑名单中
        if (connectorHostBlackList.contains(host)) {
            log.warn("checkHostValid failed, host: {}", host);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 判断网段
        try {
            IPAddressString hostAddress = new IPAddressString(host);
            for (String ips : connectorHostBlackList) {
                if (StringUtils.isEmpty(ips)) {
                    continue;
                }
                try {
                    IPAddressString ipAddress = new IPAddressString(ips);
                    if (ipAddress.contains(hostAddress) || host.contains(ips)) {
                        log.warn("checkHostValid failed, ipAddress:{}, hostAddress: {}, host: {}, ips:{}", ipAddress,
                                hostAddress, host, ips);
                        throw new AgentStudioException(StudioError.INVALID_URL);
                    }
                } catch (IllegalArgumentException e) {
                    // 忽略非法的IP格式
                    log.warn("Invalid IP format in blacklist: {}", ips);
                }
            }
        } catch (IllegalArgumentException e) {
            // host 不是合法的IP地址，可能是域名，不进行网段判断
            log.warn("Host is not a valid IP address, skip subnet check: {}", host);
        }
    }

    public PluginRequest buildFormDataRequest(String url, OkHttpUtils.Method method, Map<String, String> headers,
                                              Map<String, String> queryParams, Map<String, String> formParams, Map<String, MultipartFile> fileParams) {

        log.info("Start to build form data plugin request for the plugin!");

        Map<String, Object> combinedMap = new HashMap<>(formParams);

        for (Map.Entry<String, MultipartFile> entry : fileParams.entrySet()) {
            String key = entry.getKey();
            MultipartFile file = entry.getValue();

            // 1. 获取文件名（动态，带后缀）
            String fileName = file.getOriginalFilename();

            // 2. 获取文件字节流
            byte[] fileBytes = null;
            try {
                fileBytes = file.getBytes();
            } catch (IOException e) {
                log.error("Get inputStream from obs by url failed.", e);
            }

            // 3. 放入 combinedMap
            combinedMap.put(key, fileBytes);
            combinedMap.put("fileName", fileName);
        }

        PluginRequest pluginRequest = new PluginRequest();
        pluginRequest.setUrl(url);
        pluginRequest.setMethod(method.name());
        pluginRequest.setHeaders(headers);
        pluginRequest.setParams(queryParams);
        pluginRequest.setFormParams(combinedMap);

        return pluginRequest;
    }

    public PluginRequest buildNormalRequest(String url, OkHttpUtils.Method method, Map<String, String> headers,
                                            Map<String, String> queryParams, String jsonBody) {

        log.info("Start to build the normal request for the plugin!");

        PluginRequest pluginRequest = new PluginRequest();
        pluginRequest.setUrl(url);
        pluginRequest.setMethod(method.name());

        ObjectMapper mapper = new ObjectMapper();
        Map<String, Object> jsonMap = null;
        try {
            jsonMap = mapper.readValue(jsonBody, new TypeReference<Map<String, Object>>() { });
        } catch (JsonProcessingException e) {
            log.info("Failed to parse tool string.", e);
            throw new AgentStudioException(StudioError.OPEN_API_PARSE_FAILED);
        }
        pluginRequest.setJson(jsonMap);

        pluginRequest.setHeaders(headers);
        pluginRequest.setParams(queryParams);

        return pluginRequest;
    }
}

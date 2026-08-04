/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin.impl;

import static com.openjiuwen.studio.agent.manager.service.plugin.PluginService.parseUrl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.common.collect.Lists;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TestStatus;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.BasicInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.IsInputList;
import com.openjiuwen.studio.agent.manager.dto.plugin.IsOutputList;
import com.openjiuwen.studio.agent.manager.dto.plugin.PluginDTO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolIntfType;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolOutputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolTestStatus;
import com.openjiuwen.studio.agent.manager.dto.plugin.UrlInfo;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareInfo;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.DependencyMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.parameters.RequestBody;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.servers.Server;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Service
public class PluginBaseImpl implements IPluginBase {
    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private DependencyMapper dependencyMapper;

    // 1. 正常的注入 (实例变量)
    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Value("${mcp.encryption.domain-id:mcp-service}")
    private String mcpDomainId;

    // 2. 定义静态变量 (用于在 static 方法里使用)
    private static EncryptionAdapter staticEncryptionAdapter;

    // 3. 关键点：初始化时，把实例变量赋值给静态变量
    @PostConstruct
    public void init() {
        staticEncryptionAdapter = this.encryptionAdapter;
    }

    /**
     * 根据版本号从OBS获取工具版本定义
     *
     * @param id        toolId
     * @param versionId 版本号
     * @return ToolEntity
     */
    @Override
    public @NotNull ToolEntity getToolEntityByVersion(String id, String versionId) {
        String[] ids = id.split("#");
        String pluginId = ids[0]; // 获取 pluginId
        // 确保 toolId 存在
        String toolId = ids.length > 1 ? ids[1] : "0"; // 如果存在 toolId, 否则为 null
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(pluginId, versionId);
        if (releaseVersion == null) {
            log.error("version not exist. id={}, version={}", pluginId, versionId);
            throw new AgentStudioException(StudioError.TOOL_VERSION_NOT_EXIST, pluginId, versionId);
        }

        // 从OBS获取工具
        String toolJson = mgObsService.downloadObsFile(releaseVersion.getDslPath());
        ToolEntity toolEntity = JsonUtils.json2ObjQuietly(toolJson, ToolEntity.class);
        if (toolEntity == null) {
            PluginEntity pluginEntity = JsonUtils.json2ObjQuietly(toolJson, PluginEntity.class);
            toolEntity = transferPlugin2Tool(pluginEntity, toolId);
        }
        if (toolEntity != null && toolEntity.getInputSchema() == null) {
            PluginEntity pluginEntity = pluginMapper.selectByPrimaryKey(pluginId, null);
            toolEntity = transferPlugin2Tool(pluginEntity, toolId);
        }
        if (toolEntity == null) {
            log.error("can not parse tool entity json form obs. id={}, version={}", pluginId, versionId);
            throw new AgentStudioException(StudioError.TOOL_INFO_INCORRECT);
        }
        return toolEntity;
    }

    /**
     * 根据版本号从OBS获取工具版本定义
     *
     * @param pluginId  pluginId
     * @param versionId 版本号
     * @return ToolEntity
     */
    public @NotNull PluginEntity getPluginEntityByVersion(String pluginId, String versionId) {
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(pluginId, versionId);
        if (releaseVersion == null) {
            log.error("version not exist. id={}, version={}", pluginId, versionId);
            throw new AgentStudioException(StudioError.TOOL_VERSION_NOT_EXIST, pluginId, versionId);
        }

        // 从OBS获取工具
        String toolJson = mgObsService.downloadObsFile(releaseVersion.getDslPath());
        PluginEntity pluginEntity = JsonUtils.json2ObjQuietly(toolJson, PluginEntity.class);
        if (pluginEntity == null) {
            ToolEntity toolEntity = JsonUtils.json2ObjQuietly(toolJson, ToolEntity.class);
            if (ObjectUtils.isEmpty(toolEntity)) {
                log.error("can not parse tool entity json form obs. id={}, version={}", pluginId, versionId);
                throw new AgentStudioException(StudioError.TOOL_INFO_INCORRECT);
            }
            pluginEntity = transformTool2Plugin(toolEntity);
        }
        if (pluginEntity == null) {
            log.error("can not parse tool entity json form obs. id={}, version={}", pluginId, versionId);
            throw new AgentStudioException(StudioError.TOOL_INFO_INCORRECT);
        }
        return pluginEntity;
    }

    public static String getToolNameById(JsonNode toolInfo, String toolId, String nameField) {
        if (toolInfo != null && toolInfo.isArray()) {
            for (JsonNode tool : toolInfo) {
                JsonNode idNode = tool.get("tool_id");
                if (idNode != null && idNode.asText().equals(toolId)) {
                    JsonNode nameNode = tool.get(nameField);
                    return nameNode != null ? nameNode.asText() : toolId;
                }
            }
        }
        return toolId;
    }
    public ToolEntity transferPlugin2Tool(PluginEntity pluginEntity, String toolId) {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId(pluginEntity.getPluginId() + "#" + toolId);
        toolEntity.setProjectId(pluginEntity.getProjectId());
        toolEntity.setWorkspaceId(pluginEntity.getWorkspaceId());
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(pluginEntity.getRequestInfo());
            JsonNode toolInfo = root.get("tool_info");
            String name = getToolNameById(toolInfo, toolId, "tool_display_name");
            toolEntity.setToolDisplayName(pluginEntity.getPluginDisplayName() + name);
            toolEntity.setToolDesc(getToolNameById(toolInfo, toolId, "tool_desc"));
        } catch (IOException e) {
            throw new AgentStudioException(StudioError.TOOL_INFO_INCORRECT);
        }
        toolEntity.setToolChineseName(pluginEntity.getPluginChineseName());
        toolEntity.setIcon(pluginEntity.getIcon());
        toolEntity.setRequestInfo(buildRequestInfo(pluginEntity.getRequestInfo(), toolId));
        toolEntity.setAuthInfo(pluginEntity.getAuthInfo());
        toolEntity.setVisibility(pluginEntity.getVisibility());
        toolEntity.setInputSchema(buildInputSchema(pluginEntity.getInputSchema(), toolId));
        toolEntity.setOutputSchema(buildOutputSchema(pluginEntity.getOutputSchema(), toolId));
        toolEntity.setIsInputList(buildInputList(pluginEntity.getIsInputList(), toolId));
        toolEntity.setIsOutputList(buildOutputList(pluginEntity.getIsOutputList(), toolId));
        toolEntity.setType(pluginEntity.getType());
        toolEntity.setIntfType(buildIntfType(pluginEntity.getIntfType(), toolId));
        toolEntity.setMetadata(pluginEntity.getMetadata());
        toolEntity.setCreator(pluginEntity.getCreator());
        toolEntity.setCreatorId(pluginEntity.getCreatorId());
        toolEntity.setCreatedOn(pluginEntity.getCreatedOn());
        toolEntity.setUpdatedOn(pluginEntity.getUpdatedOn());
        toolEntity.setTestStatus(buildTestStatus(pluginEntity.getTestStatus(), toolId));
        toolEntity.setVersionId(pluginEntity.getVersionId());
        toolEntity.setAuthRequired(pluginEntity.getAuthRequired());

        return toolEntity;
    }

    @Override
    public PluginEntity transformTool2Plugin(ToolEntity toolEntity) {
        // 适配老插件的工具名称
        adaptOldEntityName(toolEntity);

        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId(toolEntity.getToolId());
        pluginEntity.setProjectId(toolEntity.getProjectId());
        pluginEntity.setWorkspaceId(toolEntity.getWorkspaceId());
        pluginEntity.setPluginDisplayName(toolEntity.getToolDisplayName());
        pluginEntity.setPluginChineseName(toolEntity.getToolChineseName());
        pluginEntity.setPluginDesc(toolEntity.getToolDesc());
        pluginEntity.setIcon(toolEntity.getIcon());
        pluginEntity.setIconName(toolEntity.getIconName());
        pluginEntity.setRequestInfo(toolEntity.getRequestInfo() == null ? null :
            buildRequestInfo(toolEntity.getRequestInfo(), toolEntity));
        pluginEntity.setAuthInfo(toolEntity.getAuthInfo());
        pluginEntity.setVisibility(toolEntity.getVisibility());
        pluginEntity.setInputSchema(toolEntity.getInputSchema() == null ? null :
            buildInputSchemaForPlugin(toolEntity.getInputSchema(), toolEntity.getRequestInfo().getHeaders()));
        pluginEntity.setOutputSchema(toolEntity.getOutputSchema() == null ? null :
            buildOutputSchemaForPlugin(toolEntity.getOutputSchema()));
        pluginEntity.setIsInputList(toolEntity.getIsInputList() == null
            ? buildIsInputListForPlugin(false)
            : buildIsInputListForPlugin(toolEntity.getIsInputList()));
        pluginEntity.setIsOutputList(toolEntity.getIsOutputList() == null
            ? buildIsOutputListForPlugin(false)
            : buildIsOutputListForPlugin(toolEntity.getIsOutputList()));
        pluginEntity.setType(toolEntity.getType());
        pluginEntity.setIntfType(toolEntity.getIntfType() == null
            ? buildIntfTypeForPlugin("blocking")
            : buildIntfTypeForPlugin(toolEntity.getIntfType()));
        pluginEntity.setMetadata(toolEntity.getMetadata());
        pluginEntity.setCreator(toolEntity.getCreator());
        pluginEntity.setCreatorId(toolEntity.getCreatorId());
        pluginEntity.setCreatedOn(toolEntity.getCreatedOn());
        pluginEntity.setUpdatedOn(toolEntity.getUpdatedOn());
        pluginEntity.setTestStatus(toolEntity.getTestStatus() == null
            ? buildTestStatusForPlugin(0)
            : buildTestStatusForPlugin(toolEntity.getTestStatus()));
        pluginEntity.setLastVersionId(toolEntity.getLastVersionId());
        pluginEntity.setCredentials(toolEntity.getCredentials());
        pluginEntity.setCredentialStatus(toolEntity.getCredentialStatus());
        pluginEntity.setVersionId(toolEntity.getVersionId());
        pluginEntity.setCustomizeNode(toolEntity.getCustomizeNode());
        pluginEntity.setAuthRequired(toolEntity.getAuthRequired());
        pluginEntity.setTraceId(toolEntity.getTraceId());
        pluginEntity.setPublished(toolEntity.getPublished());
        pluginEntity.setCallMode("api");
        return pluginEntity;
    }

    private String buildIntfType(String intfType, String toolId) {
        List<ToolIntfType> intType;
        if (StringUtils.isEmpty(intfType)) {
            return "blocking";
        }
        try {
            intType = JsonUtils.JSON_MAPPER.readValue(intfType,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolIntfType.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse buildIntfType to ToolInfo", e);
            throw new AgentStudioException(StudioError.PARSE_BUILD_INT_TYPE_FAILED);
        }
        return intType.stream()
            .filter(target -> target.getToolId().equals(toolId))
            .findFirst()
            .map(ToolIntfType::getIntfType)
            .orElseGet(() ->
                intType.stream()
                    .filter(target -> target.getToolId().equals("0"))
                    .findFirst()
                    .map(ToolIntfType::getIntfType)
                    .orElse("blocking")
            );
    }

    private Integer buildTestStatus(String input, String toolId) {
        List<ToolTestStatus> testStatus;
        if (StringUtils.isEmpty(input)) {
            return 0;
        }
        try {
            testStatus = JsonUtils.JSON_MAPPER.readValue(input,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolTestStatus.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse buildTestStatus to ToolInfo", e);
            throw new AgentStudioException(StudioError.BUILD_STATUS_TOOL_FAILED);
        }
        return testStatus.stream()
            .filter(target -> target.getToolId().equals(toolId))
            .findFirst()
            .map(ToolTestStatus::getTestStatus)
            .orElseGet(() ->
                testStatus.stream()
                    .filter(target -> target.getToolId().equals("0"))
                    .findFirst()
                    .map(ToolTestStatus::getTestStatus)
                    .orElse(0)
            );

    }

    private String buildOutputSchema(String outputSchema, String toolId) {
        List<ToolOutputSchema> toolOutputSchemas;
        if (StringUtils.isEmpty(outputSchema)) {
            return JsonUtils.toJson(new ToolOutputSchema());
        }
        try {
            toolOutputSchemas = JsonUtils.JSON_MAPPER.readValue(outputSchema,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolOutputSchema.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse requestInfo to buildOutputSchema", e);
            throw new AgentStudioException(StudioError.PARSE_OUTPUT_SCHEMA_TOOL_FAILED);
        }
        ToolOutputSchema toolInput = toolOutputSchemas.stream()
            .filter(toolInputSchema -> toolInputSchema.getToolId().equals(toolId))
            .findFirst()
            .orElse(null);
        if (toolInput == null) {
            toolInput = toolOutputSchemas.stream()
                .filter(toolInputSchema -> toolInputSchema.getToolId().equals("0"))
                .findFirst()
                .orElse(new ToolOutputSchema());
        }
        return toolInput.getOutputSchema();
    }

    private String buildInputSchema(String inputSchema, String toolId) {
        ToolInputSchema toolInput = filterToolInputSchema(inputSchema, toolId);
        return toolInput.getInputSchema();
    }

    private Boolean buildOutputList(String isOutputList, String toolId) {
        List<IsOutputList> isOutputLists;
        if (StringUtils.isEmpty(isOutputList)) {
            return false;
        }
        try {
            isOutputLists = JsonUtils.JSON_MAPPER.readValue(isOutputList,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, IsOutputList.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse buildOutputList to ToolInfo", e);
            throw new AgentStudioException(StudioError.PARSE_BUILD_OUTPUT_LIST_FAILED);
        }
        return isOutputLists.stream()
            .filter(target -> target.getToolId().equals(toolId))
            .findFirst()
            .map(IsOutputList::isList)
            .orElseGet(() ->
                isOutputLists.stream()
                    .filter(target -> target.getToolId().equals("0"))
                    .findFirst()
                    .map(IsOutputList::isList)
                    .orElse(false)
            );
    }

    private Boolean buildInputList(String isInputList, String toolId) {
        List<IsInputList> isInputLists;
        if (StringUtils.isEmpty(isInputList)) {
            return false;
        }
        try {
            isInputLists = JsonUtils.JSON_MAPPER.readValue(isInputList,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, IsInputList.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse buildInputList to ToolInfo", e);
            throw new AgentStudioException(StudioError.PARSE_INPUT_SCHEMA_TOOL_FAILED);
        }
        return isInputLists.stream()
            .filter(target -> target.getToolId().equals(toolId))
            .findFirst()
            .map(IsInputList::isList)
            .orElseGet(() ->
                isInputLists.stream()
                    .filter(target -> target.getToolId().equals("0"))
                    .findFirst()
                    .map(IsInputList::isList)
                    .orElse(false)
            );
    }

    private ToolInputSchema filterToolInputSchema(String inputSchema, String toolId) {
        List<ToolInputSchema> toolInputSchemaList;
        if (StringUtils.isEmpty(inputSchema)) {
            return new ToolInputSchema();
        }
        try {
            toolInputSchemaList = JsonUtils.JSON_MAPPER.readValue(inputSchema,
                JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolInputSchema.class));
        } catch (JsonProcessingException e) {
            log.error("Failed to parse requestInfo to filterToolInputSchema", e);
            throw new AgentStudioException(StudioError.PARSE_filter_SCHEMA_TOOL_FAILED);
        }
        ToolInputSchema toolInput = toolInputSchemaList.stream()
            .filter(toolInputSchema -> toolInputSchema.getToolId().equals(toolId))
            .findFirst()
            .orElse(null);
        if (toolInput == null) {
            toolInput = toolInputSchemaList.stream()
                .filter(toolInputSchema -> toolInputSchema.getToolId().equals("0"))
                .findFirst()
                .orElse(new ToolInputSchema());
        }
        return toolInput;
    }

    private RequestInfo buildRequestInfo(String requestInfoStr, String toolId) {
        ToolRequestInfo newTtoolRequestInfo;
        RequestInfo requestInfo = new RequestInfo();
        if (StringUtils.isEmpty(requestInfoStr)) {
            return requestInfo;
        }
        try {
            JsonNode requestInfojsonNode = JsonUtils.JSON_MAPPER.readTree(
                ObjectUtils.isEmpty(requestInfoStr) ? "{}" : requestInfoStr);

            newTtoolRequestInfo = JsonUtils.JSON_MAPPER.treeToValue(requestInfojsonNode, ToolRequestInfo.class);

        } catch (JsonProcessingException e) {
            log.error("Failed to parse requestInfo to ToolInfo {}", e.getMessage());
            throw new AgentStudioException(StudioError.PARSE_REQUEST_TO_TOOL_FAILED);
        }
        ToolInfo toolInfo = newTtoolRequestInfo.getToolsInfoList()
            .stream()
            .filter(toolInfo1 -> toolInfo1.getToolId().equals(toolId))
            .findFirst()
            .orElse(null);

        if (toolInfo == null) {
            toolInfo = newTtoolRequestInfo.getToolsInfoList()
                .stream()
                .filter(toolInfo1 -> toolInfo1.getToolId().equals("0"))
                .findFirst()
                .orElse(new ToolInfo());
        }

        requestInfo.setUrl(
            newTtoolRequestInfo.getBasicInfo().getProtocol() + "://" + newTtoolRequestInfo.getBasicInfo().getHost()
                + newTtoolRequestInfo.getBasicInfo().getPath() + toolInfo.getPath());
        requestInfo.setMethod(RequestInfo.MethodEnum.fromValue(toolInfo.getMethod()));
        requestInfo.setPathParams(toolInfo.getPathParams());
        requestInfo.setInputSchema(newTtoolRequestInfo.getBasicInfo().getInputSchema());
        return requestInfo;
    }

    public Map<String, String> extractContentType(String inputSchema) {
        Map<String, String> header = new HashMap<>();

        JSONObject jsonObject = JSONObject.parseObject(inputSchema);
        JSONObject properties = jsonObject.getJSONObject("properties");

        if (properties.containsKey(CommonConstant.CONTENT_TYPE)) {
            JSONObject contentType = properties.getJSONObject(CommonConstant.CONTENT_TYPE);
            String defaultValue = contentType.getString("default");
            header.put(CommonConstant.CONTENT_TYPE, defaultValue);
        } else {
            header.put(CommonConstant.CONTENT_TYPE, CommonConstant.APPLICATION_JSON);
        }

        return header;
    }

    @Override
    public ToolEntity buildToolByPlugin(String projectId, String workspaceId, String pluginId, String toolId) {
        log.info(">>>buildToolByPlugin query plugin");
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, null, null);
        ToolEntity newTool = toolMapper.selectWithoutStatus(pluginId, null, null);
        if (Objects.isNull(pluginEntity)) {
            log.error("plugin:{} not exist", pluginId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, String.format("plugin %s not exist", pluginId));
        }

        if (!Strings.CS.equals(pluginEntity.getType(), ToolType.INNER.type)) {
            // 插件详情页插件调测功能，插件信息从数据库表里取
            log.info(">>>buildToolByPlugin inner plugin");
            pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, null, workspaceId);
            newTool = toolMapper.selectWithoutStatus(pluginId, null, workspaceId);
        }

        if (Objects.isNull(pluginEntity)) {
            log.error(">>>buildToolByPlugin plugin not exist");
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST, String.format("plugin %s not exist", pluginId));
        }
        newTool.setToolId(pluginId + "#0");
        newTool.setIsFree(pluginEntity.getIsFree() != null ? pluginEntity.getIsFree() : 0);
        String inputSchema = null;
        if (StringUtils.isNotBlank(pluginEntity.getInputSchema()) && pluginEntity.getInputSchema()
            .contains("tool_id")) {
            List<ToolInputSchema> inputSchemas = JSON.parseArray(pluginEntity.getInputSchema(), ToolInputSchema.class);
            for (ToolInputSchema item : inputSchemas) {
                if (toolId.equals(item.getToolId())) { // 假设 tool_id 是已定义的变量
                    inputSchema = item.getInputSchema();
                    newTool.setInputSchema(inputSchema);
                    newTool.setToolId(pluginId + "#" + toolId);
                    break;
                }
            }
        }
        log.info(">>>buildToolByPlugin analysis schema");
        if (StringUtils.isNotBlank(pluginEntity.getOutputSchema()) && pluginEntity.getOutputSchema()
            .contains("tool_id")) {
            List<ToolOutputSchema> outputSchemas = JSON.parseArray(pluginEntity.getOutputSchema(),
                ToolOutputSchema.class);
            for (ToolOutputSchema schema : outputSchemas) {
                if (schema.getToolId() != null && schema.getToolId().equals(toolId)) {
                    newTool.setOutputSchema(schema.getOutputSchema());
                    break;
                }
            }
        }
        log.info(">>>buildToolByPlugin request info");
        if (StringUtils.isNotBlank(pluginEntity.getRequestInfo())) {
            if (pluginEntity.getRequestInfo().contains("basic_info")) {
                JSONObject jsonObject = JSON.parseObject(pluginEntity.getRequestInfo());
                List<ToolInfo> toolsInfo = jsonObject.getList("tool_info", ToolInfo.class);
                BasicInfo basicInfo = jsonObject.getObject("basic_info", BasicInfo.class);

                // 查找匹配的 tool_id
                ToolInfo matchedToolInfo = toolsInfo.stream()
                    .filter(tool -> tool.getToolId() != null && tool.getToolId().equals(toolId))
                    .findFirst()
                    .orElse(null);

                if (matchedToolInfo != null) {
                    newTool.setRequestInfo(
                        new RequestInfo().setUrl(basicInfo.getProtocol() + "://" + basicInfo.getHost() + basicInfo.getPath()+ matchedToolInfo.getPath())
                            .setMethod(RequestInfo.MethodEnum.valueOf(matchedToolInfo.getMethod())).setInputSchema(basicInfo.getInputSchema()).setHeaders(extractContentType(inputSchema)));
                } else {
                    // 未找到匹配的 tool_id
                    log.error("request info is null please check plugin {}", pluginEntity.getPluginId());
                    throw new AgentStudioException(StudioError.TOOL_INPUT_INVALID);
                }
            }
        } else {
            // 未知格式
            log.error("request info is null please check plugin {}", pluginEntity.getPluginId());
            throw new AgentStudioException(StudioError.TOOL_INPUT_INVALID);
        }
        log.info(">>>buildToolByPlugin interface type");
        if (StringUtils.isNotBlank(pluginEntity.getIntfType()) && pluginEntity.getIntfType().contains("tool_id")) {
            List<ToolIntfType> intfTypes = JSON.parseArray(pluginEntity.getIntfType(), ToolIntfType.class);
            for (ToolIntfType intfType : intfTypes) {
                if (toolId.equals(intfType.getToolId())) {
                    newTool.setIntfType(intfType.getIntfType());
                    break;
                }
            }
        }
        log.info(">>>buildToolByPlugin test status");
        if (StringUtils.isNotBlank(pluginEntity.getTestStatus())) {
            if (pluginEntity.getTestStatus().contains("tool_id")) {
                List<ToolTestStatus> testStatusList = JSON.parseArray(pluginEntity.getTestStatus(), ToolTestStatus.class);
                for (ToolTestStatus testStatus : testStatusList) {
                    if (toolId.equals(testStatus.getToolId())) {
                        newTool.setTestStatus(testStatus.getTestStatus());
                        break;
                    }
                }
            } else if (pluginEntity.getTestStatus().equals("[]")) {
                // 没有状态，默认为UNKNOWN
                newTool.setTestStatus(TestStatus.UNKNOWN.getCode());
            } else {
                newTool.setTestStatus(toolMapper.selectStatus(pluginId, projectId, workspaceId));
            }
        }
        log.info(">>>buildToolByPlugin input list & output list");
        if (StringUtils.isNotBlank(pluginEntity.getIsInputList())) {
            if (pluginEntity.getIsInputList().contains("tool_id")) {
                List<IsInputList> isInputLists = JSON.parseArray(pluginEntity.getIsInputList(), IsInputList.class);
                for (IsInputList inputList : isInputLists) {
                    if (toolId.equals(inputList.getToolId())) {
                        newTool.setIsInputList(inputList.isList());
                        break;
                    }
                }
            } else {
                newTool.setIsInputList(toolMapper.selectIsInputList(pluginId));
            }
        }

        if (StringUtils.isNotBlank(pluginEntity.getIsOutputList())) {
            if (pluginEntity.getIsOutputList().contains("tool_id")) {
                List<IsOutputList> isOutputLists = JSON.parseArray(pluginEntity.getIsOutputList(), IsOutputList.class);
                for (IsOutputList outputList : isOutputLists) {
                    if (toolId.equals(outputList.getToolId())) {
                        newTool.setIsOutputList(outputList.isList());
                        break;
                    }
                }
            } else {
                newTool.setIsOutputList(toolMapper.selectIsOutputList(pluginId));
            }
        }

        newTool.setAuthInfo(pluginEntity.getAuthInfo());

        return newTool;
    }

    private String buildIntfTypeForPlugin(String intfType) {
        ToolIntfType toolIntfType = ToolIntfType.builder().toolId("0").intfType(intfType).build();
        return JsonUtils.toJson(Collections.singleton(toolIntfType));
    }

    private String buildOutputSchemaForPlugin(String outputSchema) {
        ToolOutputSchema toolOutputSchema = ToolOutputSchema.builder().toolId("0").outputSchema(outputSchema).build();
        return JsonUtils.toJson(Collections.singleton(toolOutputSchema));
    }

    private String buildInputSchemaForPlugin(String inputSchema, Map<String, String> headers) {
        String result = inputSchema;
        if (StringUtils.isNotEmpty(inputSchema)) {
            try {
                result = fillHeaders(inputSchema, headers);
            } catch (IOException e) {
                log.error("parse header failed! {}", headers);
            }
        }
        ToolInputSchema toolInputSchema = ToolInputSchema.builder().toolId("0").inputSchema(result).build();
        return JsonUtils.toJson(Collections.singleton(toolInputSchema));
    }

    @Override
    public List<ToolInputSchema> buildInputSchemaForOld(String inputSchema, Map<String, String> headers) {
        String result = inputSchema;
        if (StringUtils.isNotEmpty(inputSchema)) {
            try {
                result = fillHeaders(inputSchema, headers);
            } catch (IOException e) {
                log.error("parse header failed! {}", headers);
            }
        }
        ToolInputSchema toolInputSchema = ToolInputSchema.builder().toolId("0").inputSchema(result).build();
        List<ToolInputSchema> toolInputSchemaList = new ArrayList<>();
        toolInputSchemaList.add(toolInputSchema);
        return toolInputSchemaList;
    }

    @Override
    public boolean validateAuth(String projectId, String workspaceId, Map<String, Object> configs) {
        if (MapUtils.isEmpty(configs) || !configs.containsKey("id")) {
            return false;
        }
        String pluginId = configs.get("id").toString();
        PluginEntity pluginEntity = pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(pluginId, null, workspaceId);
        String credentialStatus = pluginEntity.getCredentialStatus();
        if (Strings.CI.equals(credentialStatus, Constants.AUTHENTICATED) || Strings.CI.equals(credentialStatus, Constants.AUTHENTICATED_NONE)) {
            return true;
        } else {
            log.info("plugin {} is preplugin but not authenticated", pluginId);
            return Strings.CI.equals(credentialStatus, Constants.UNAUTHENTICATED) && pluginEntity.getIsFree() != null && pluginEntity.getIsFree().equals(1);
        }
    }

    /**
     * 校验插件的输入参数、工具的输入参数是否重名
     * @param toolInputSchemas 工具的输入参数
     * @param toolRequestInfo  插件的基本信息
     */
    @Override
    public void validateDuplicateInputSchema(List<ToolInputSchema> toolInputSchemas, ToolRequestInfo toolRequestInfo) {
        log.info("Start to validate input schema!");
        BasicInfo basicInfo = toolRequestInfo.getBasicInfo();
        if (Objects.isNull(basicInfo) || StringUtils.isBlank(basicInfo.getInputSchema())) {
            return;
        }

        SchemaConfig pluginInputSchema = JSON.parseObject(basicInfo.getInputSchema(), SchemaConfig.class);
        Map<String, SchemaConfig> pluginInfo = pluginInputSchema.getProperties();

        for (ToolInputSchema inputSchema : toolInputSchemas) {
            if (StringUtils.isBlank(inputSchema.getInputSchema())) {
                continue;
            }
            SchemaConfig toolInputSchema = JSON.parseObject(inputSchema.getInputSchema(), SchemaConfig.class);
            Map<String, SchemaConfig> toolInfo = toolInputSchema.getProperties();

            for (Map.Entry<String, SchemaConfig> item : pluginInfo.entrySet()) {
                String name = item.getKey();
                if (toolInfo.containsKey(name)) {
                    log.info("Duplicate parameter names found! Please re-enter the parameter names.");
                    throw new AgentStudioException(StudioError.DUPLICATE_PARAMETER_NAME_EXCEPTION);
                }
            }
        }
    }

    /**
     * 处理shareInfo中的resource id,替换为新的resource id
     * @param tool tool
     */
    @Override
    public void adaptToolShareInfo(ToolEntity tool) {
        log.info("Start to adapt share info");
        ShareInfo shareInfo = tool.getShareInfo();
        if (Objects.isNull(shareInfo)) {
            return;
        }
        shareInfo.setResourceId(tool.getToolId());

        shareInfo.getShareScopeEntityList().forEach(shareScopeEntity -> {
            shareScopeEntity.setResourceId(tool.getToolId());
        });
    }

    /**
     * 将openAPI对象转化为插件定义
     *
     * @param openAPI openAPI对象
     * @return PluginDTO
     */
    @Override
    public PluginDTO transformOpenAPI2Plugin(OpenAPI openAPI) {
        if (openAPI == null) {
            throw new AgentStudioException(StudioError.OPENAPI_FILE_NOT_EXIST);
        }
        PluginDTO pluginDTO = buildPluginDefault();
        // 基本信息
        pluginDTO.setPluginChineseName(openAPI.getInfo().getTitle());
        pluginDTO.setPluginDisplayName(openAPI.getInfo().getTitle());
        pluginDTO.setPluginDesc(openAPI.getInfo().getDescription());

        AtomicBoolean getFailed = new AtomicBoolean(true);
        AtomicBoolean postFailed = new AtomicBoolean(true);
        // requestInfo
        ToolRequestInfo toolRequestInfo = new ToolRequestInfo();
        List<Server> servers = openAPI.getServers();
        if (servers == null || servers.isEmpty()) {
            throw new AgentStudioException(StudioError.SERVER_NOT_EXIST);
        }
        String url = servers.get(0).getUrl();
        if (url == null || url.trim().isEmpty()) {
            throw new AgentStudioException(StudioError.SERVER_URL_NOT_EXIST);
        }
        UrlInfo urlInfo = parseUrl(url);
        // basicInfo
        BasicInfo basicInfo = BasicInfo.builder()
            .host(urlInfo.getHost())
            .protocol(urlInfo.getProtocol())
            .path(urlInfo.getBasePath())
            .build();
        toolRequestInfo.setBasicInfo(basicInfo);
        // tools
        List<ToolInfo> toolsInfoList = new ArrayList<>();

        List<ToolInputSchema> toolInputSchemaList = new ArrayList<>();

        List<ToolOutputSchema> toolOutputSchemaList = new ArrayList<>();

        openAPI.getPaths().forEach((path, pathItem) -> {
            try {
                // 获取 GET 操作
                Operation getOperation = pathItem.getGet();
                String getId = generateShortBitId();
                path = (path != null && path.startsWith("/")) ? path.substring(1) : path;
                if (getOperation != null) {
                    ToolInfo toolInfo = ToolInfo.builder()
                        .toolId(getId)
                        .toolChineseName(getOperation.getOperationId())
                        .toolDisplayName(getOperation.getOperationId())
                        .path(path)
                        .method("GET")
                        .toolDesc(getOperation.getDescription() == null ? "Import Get Method" : getOperation.getDescription())
                        .build();
                    toolsInfoList.add(toolInfo);

                    // 1. 构建输入 Schema
                    SchemaConfig inputSchemaConfig = new SchemaConfig();
                    inputSchemaConfig.setType("object");
                    inputSchemaConfig.setProperties(new HashMap<>());
                    inputSchemaConfig.setRequired(new ArrayList<>());

                    // 解析参数
                    getFailed.set(parseParameters(inputSchemaConfig, getOperation.getParameters(), openAPI));

                    // 2. 构建输出 Schema
                    SchemaConfig outputSchemaConfig = new SchemaConfig();
                    outputSchemaConfig.setType("object");
                    outputSchemaConfig.setProperties(new HashMap<>());
                    outputSchemaConfig.setRequired(new ArrayList<>());

                    // 安全获取 200 响应
                    ApiResponse response200 = getOperation.getResponses() != null
                        ? getOperation.getResponses().get("200") : null;

                    if (response200 == null) {
                        log.warn("No 200 response defined for GET operation: {}", getOperation.getOperationId());
                        // 可选：设置默认空对象或跳过
                    } else {
                        getFailed.set(parseResponse(outputSchemaConfig, response200, openAPI));
                    }

                    // 3. 添加到工具 Schema 列表
                    toolInputSchemaList.add(new ToolInputSchema(getId, JsonUtils.toJson(inputSchemaConfig)));
                    toolOutputSchemaList.add(new ToolOutputSchema(getId, JsonUtils.toJson(outputSchemaConfig)));
                }
            } catch (AgentStudioException e) {
                log.error("GET processing exception.: {}", path, e);
                throw new AgentStudioException(StudioError.OPENAPI_PARSE_FAILED);
            }

            try {
                // 获取 POST 操作
                Operation postOperation = pathItem.getPost();
                String postId = generateShortBitId();
                path = (path != null && path.startsWith("/")) ? path.substring(1) : path;
                if (postOperation != null) {
                    ToolInfo toolInfo = ToolInfo.builder()
                        .toolId(postId)
                        .toolChineseName(postOperation.getOperationId())
                        .toolDisplayName(postOperation.getOperationId())
                        .path(path)
                        .method("POST")
                        .toolDesc(postOperation.getDescription() == null ? "Import Post Method" : postOperation.getDescription())
                        .build();
                    toolsInfoList.add(toolInfo);

                    // 1. 构建输入 Schema
                    SchemaConfig inputSchemaConfig = new SchemaConfig();
                    inputSchemaConfig.setType("object");
                    inputSchemaConfig.setProperties(new HashMap<>());
                    inputSchemaConfig.setRequired(new ArrayList<>());


                    // 解析参数
                    postFailed.set(parseParameters(inputSchemaConfig, postOperation.getParameters(), openAPI));

                    // 2. 构建输出 Schema
                    SchemaConfig outputSchemaConfig = new SchemaConfig();
                    outputSchemaConfig.setType("object");
                    outputSchemaConfig.setProperties(new HashMap<>());
                    outputSchemaConfig.setRequired(new ArrayList<>());

                    postFailed.set(parseRequestBody(inputSchemaConfig, postOperation.getRequestBody(), openAPI));

                    // 安全获取 200 响应
                    ApiResponse response200 = postOperation.getResponses() != null
                        ? postOperation.getResponses().get("200") : null;

                    if (response200 == null) {
                        log.warn("No 200 response defined for POST operation: {}", postOperation.getOperationId());
                    } else {
                        postFailed.set(parseResponse(outputSchemaConfig, response200, openAPI));
                    }

                    // 3. 添加到工具 Schema 列表
                    toolInputSchemaList.add(new ToolInputSchema(postId, JsonUtils.toJson(inputSchemaConfig)));
                    toolOutputSchemaList.add(new ToolOutputSchema(postId, JsonUtils.toJson(outputSchemaConfig)));
                }
            } catch (AgentStudioException e) {
                log.error("POST processing exception.: {}", path, e);
                throw new AgentStudioException(StudioError.OPENAPI_PARSE_FAILED);
            }
        });

        if (!getFailed.get() && !postFailed.get()) {
            throw new AgentStudioException(StudioError.OPENAPI_PARSE_FAILED);
        }
        toolRequestInfo.setToolsInfoList(toolsInfoList);
        pluginDTO.setToolRequestInfo(toolRequestInfo);
        pluginDTO.setToolInputSchemaList(toolInputSchemaList);
        pluginDTO.setToolOutputSchemaList(toolOutputSchemaList);
        return pluginDTO;
    }

    private PluginDTO buildPluginDefault() {
        PluginDTO pluginDTO = new PluginDTO();
        pluginDTO.setAuthInfo(new AuthInfo());
        pluginDTO.setAuthRequired(false);
        pluginDTO.setVisibility("project");
        pluginDTO.setCallMode("api");
        pluginDTO.setCreatedOn(new Date());
        pluginDTO.setType("custom");
        return pluginDTO;
    }

    private boolean parseParameters(SchemaConfig schemaConfig, List<Parameter> parameters, OpenAPI openAPI) {
        if (parameters == null || parameters.isEmpty()) {
            log.warn("Invalid parseParameters: Parameters is null");
            return false;
        }
        parameters.forEach(parameter -> {
            SchemaConfig property = new SchemaConfig();
            property.setDescription(parameter.getDescription());
            property.setType(parameter.getSchema() != null ? parameter.getSchema().getType() : null);
            // OpenAPI 规范 in 值为小写 (query/header/path)，运行时要求首字母大写 (Query/Headers/Path)
            String rawIn = parameter.getIn();
            String mappedLocation = switch (rawIn != null ? rawIn : "") {
                case "query" -> "Query";
                case "header" -> "Headers";
                case "path" -> "Path";
                default -> "Body";
            };
            property.setLocation(mappedLocation);
            if (parameter.getSchema() != null && parameter.getSchema().getDefault() != null) {
                property.setDefaultValue(String.valueOf(parameter.getSchema().getDefault()));
            }
            schemaConfig.getProperties().put(parameter.getName(), property);
        });
        return true;
    }

    private boolean parseRequestBody(SchemaConfig schemaConfig, RequestBody requestBody, OpenAPI openAPI) {
        if (requestBody == null || requestBody.getContent() == null || requestBody.getContent().isEmpty()) {
            log.warn("Invalid parseRequestBody: RequestBody is null");
            return false;
        }
        MediaType mediaType = requestBody.getContent().get("application/json");

        return parseMediaType(schemaConfig, mediaType, openAPI);
    }

    private boolean parseResponse(SchemaConfig schemaConfig, ApiResponse apiResponse, OpenAPI openAPI) {
        if (apiResponse == null || apiResponse.getContent() == null || apiResponse.getContent().isEmpty()) {
            log.warn("Invalid 200 response: no content defined for operation");
            return false;
        }

        MediaType mediaType = apiResponse.getContent().get("application/json");

        return parseMediaType(schemaConfig, mediaType, openAPI);
    }

    private boolean parseMediaType(SchemaConfig schemaConfig, MediaType mediaType, OpenAPI openAPI) {
        if (mediaType == null || mediaType.getSchema() == null) {
            log.warn("Invalid parseMediaType: MediaType is null");
            return false;
        }
        Schema<?> schema = mediaType.getSchema();

        schema = resolveReference(schema, openAPI);

        Map<String, SchemaConfig> newProperties = new LinkedHashMap<>();

        if (schema.getProperties() != null) {
            schema.getProperties().forEach((propertyName, propertySchema) -> {
                if (propertySchema != null) {
                    newProperties.put(propertyName, parseSchema(propertySchema, openAPI));
                }
            });
        }

        // 如果是数组类型，处理items
        if ("array".equals(schema.getType()) && schema.getItems() != null) {
            SchemaConfig itemConfig = parseSchema(schema.getItems(), openAPI);
            schemaConfig.setItems(itemConfig);
        }

        // 批量写入，避免并发修改异常
        schemaConfig.getProperties().putAll(newProperties);
        return true;
    }

    public SchemaConfig parseSchema(Schema<?> schema, OpenAPI openAPI) {
        schema = resolveReference(schema, openAPI);
        SchemaConfig schemaConfig = new SchemaConfig();
        schemaConfig.setDescription(schema.getDescription());
        schemaConfig.setType(schema.getType());
        // location 只在inputSchema生效
        schemaConfig.setLocation("Body");
        // 处理嵌套属性
        if (schema.getProperties() != null && !schema.getProperties().isEmpty()) {
            Map<String, SchemaConfig> newProperties = new LinkedHashMap<>();
            schema.getProperties().forEach((propertyName, propertySchema) -> {
                newProperties.put(propertyName, parseSchema(propertySchema, openAPI));
            });
            schemaConfig.setProperties(newProperties);
        }

        // 处理数组
        if ("array".equals(schema.getType()) && schema.getItems() != null) {
            schemaConfig.setItems(parseSchema(schema.getItems(), openAPI));
        }
        return schemaConfig;
    }

    // 新增的方法：解析引用
    public Schema<?> resolveReference(Schema<?> schema, OpenAPI openAPI) {
        // 检查是否有$ref
        String ref = schema.get$ref();
        if (ref != null && !ref.isEmpty()) {
            log.debug("Resolving reference: {}", ref);

            // 处理不同格式的引用
            if (ref.startsWith("#/components/schemas/")) {
                String schemaName = ref.substring("#/components/schemas/".length());
                Schema<?> resolved = openAPI.getComponents().getSchemas().get(schemaName);
                if (resolved != null) {
                    // 递归解析（引用可能指向另一个引用）
                    return resolveReference(resolved, openAPI);
                }
            }
            // 可以添加对其他类型引用的支持
        }
        return schema;
    }

    public static String generateShortBitId() {
        // 生成标准UUID并去除连接符，得到32位字符串
        String uuid = UUID.randomUUID().toString().replace("-", "");
        // 截取前16位（也可截取后16位：uuid.substring(16)）
        return uuid.substring(0, 8);
    }

    private String buildTestStatusForPlugin(Integer testStatus) {
        ToolTestStatus toolTestStatus = ToolTestStatus.builder().toolId("0").testStatus(testStatus).build();
        return JsonUtils.toJson(Collections.singleton(toolTestStatus));
    }

    private String buildIsInputListForPlugin(Boolean input) {
        IsInputList isInputList = IsInputList.builder().toolId("0").isList(input).build();
        return JsonUtils.toJson(Collections.singleton(isInputList));
    }

    private String buildIsOutputListForPlugin(Boolean input) {
        IsOutputList isOutputList = IsOutputList.builder().toolId("0").isList(input).build();
        return JsonUtils.toJson(Collections.singleton(isOutputList));
    }

    private String buildRequestInfo(RequestInfo requestInfo, ToolEntity toolEntity) {
        ToolRequestInfo toolRequestInfo = new ToolRequestInfo();
        UrlInfo urlInfo = parseUrl(requestInfo.getUrl());
        BasicInfo basicInfo = BasicInfo.builder()
            .host(urlInfo.getHost())
            .protocol(urlInfo.getProtocol())
            .path("")
            .build();
        toolRequestInfo.setBasicInfo(basicInfo);

        ToolInfo toolInfo = new ToolInfo();
        // 提取path
        toolInfo.setToolId("0");
        toolInfo.setToolDisplayName(toolEntity.getToolDisplayName());
        toolInfo.setToolChineseName(toolEntity.getToolChineseName());
        toolInfo.setToolDesc(toolEntity.getToolDesc());
        toolInfo.setPath(urlInfo.getBasePath());
        toolInfo.setMethod(toolEntity.getRequestInfo().getMethod().toString());
        toolRequestInfo.setToolsInfoList(Lists.newArrayList());
        toolRequestInfo.getToolsInfoList().add(toolInfo);
        return JsonUtils.toJson(toolRequestInfo);
    }

    private String fillHeaders(String jsonSchema, Map<String, String> headers) throws IOException {
        if (MapUtils.isEmpty(headers)) {
            return jsonSchema;
        }
        ObjectMapper mapper = new ObjectMapper();
        JsonNode rootNode;
        try {
            rootNode = mapper.readTree(jsonSchema);
        } catch (JsonProcessingException e) {
            throw new IOException("Invalid JSON schema format: " + e.getMessage(), e);
        }
        // 1. 先查找是否存在Headers参数
        JsonNode propertiesNode = rootNode.path("properties");
        ObjectNode objectNode = (ObjectNode) propertiesNode;
        JsonNode requiredNode = rootNode.path("required");
        ArrayNode arrayNode;
        arrayNode = ObjectUtils.isEmpty(requiredNode) ? mapper.createArrayNode() : (ArrayNode) requiredNode;

        for (Map.Entry<String, String> entry : headers.entrySet()) {
            Map<String, Object> propertiesEntry = new HashMap<>();
            propertiesEntry.put("defaultValue", entry.getValue());
            propertiesEntry.put("default", entry.getValue());
            propertiesEntry.put("location", "Headers");
            propertiesEntry.put("validate_rule", "");
            propertiesEntry.put("validate_type", "CHAR");
            propertiesEntry.put("validated", false);
            propertiesEntry.put("name_cn", "");
            propertiesEntry.put("type", "string");
            propertiesEntry.put("description", "");
            objectNode.putPOJO(entry.getKey(), propertiesEntry);
            arrayNode.add(entry.getKey());
        }
        return rootNode.toString();
    }

    public void adaptOldEntityName(ToolEntity plugin) {
        if (StringUtils.isEmpty(plugin.getToolDisplayName())) {
            plugin.setToolDisplayName(plugin.getToolChineseName());
        }
        if (StringUtils.isEmpty(plugin.getToolChineseName())) {
            plugin.setToolChineseName(plugin.getToolDisplayName());
        }
    }

    /**
     * 插件entity -> dto
     * @param pluginEntity
     * @return dto
     */
    @Override
    public PluginDTO transformEntityToDTO(PluginEntity pluginEntity) {
        ToolInfo toolInfo = null;
        ToolRequestInfo toolRequestInfo = null;
        boolean isNewPluginEntity = false;

        try {
            JsonNode requestInfojsonNode = JsonUtils.JSON_MAPPER.readTree(
                    ObjectUtils.isEmpty(pluginEntity.getRequestInfo()) ? "{}" : pluginEntity.getRequestInfo());
            if (requestInfojsonNode.has("basic_info")) {
                toolRequestInfo = JsonUtils.JSON_MAPPER.treeToValue(requestInfojsonNode, ToolRequestInfo.class);
                isNewPluginEntity = true;
            } else {
                toolInfo = JsonUtils.JSON_MAPPER.treeToValue(requestInfojsonNode, ToolInfo.class);
            }

        } catch (JsonProcessingException e) {
            log.error("Failed to parse requestInfo to ToolInfo", e);
            throw new AgentStudioException(StudioError.PARSE_REQUEST_TO_TOOL_FAILED);
        }

        if (isNewPluginEntity) {
            return transformNewEntityToDTO(toolRequestInfo, pluginEntity);
        }

        PluginDTO pluginDTO = new PluginDTO();
        BeanUtils.copyProperties(pluginEntity, pluginDTO);

        String toolId = "0";

        // 构建OutputSchema字段
        ToolOutputSchema toolOutputSchema = ToolOutputSchema.builder()
                .toolId(toolId)
                .outputSchema(pluginEntity.getOutputSchema())
                .build();
        List<ToolOutputSchema> toolOutputSchemaList = new ArrayList<>();
        toolOutputSchemaList.add(toolOutputSchema);

        // 构建IntfType字段
        ToolIntfType toolIntfType = ToolIntfType.builder().toolId(toolId).intfType(pluginEntity.getIntfType()).build();
        List<ToolIntfType> toolIntfTypes = new ArrayList<>();
        toolIntfTypes.add(toolIntfType);

        // 构建TestStatus字段
        ToolTestStatus toolTestStatus = ToolTestStatus.builder()
                .toolId(toolId)
                .testStatus(pluginEntity.getTestStatus() != null
                        ? Integer.parseInt(pluginEntity.getTestStatus())
                        : TestStatus.UNKNOWN.getCode())
                .build();
        List<ToolTestStatus> toolTestStatusList = new ArrayList<>();
        toolTestStatusList.add(toolTestStatus);

        IsInputList isInputList = IsInputList.builder()
                .toolId(toolId)
                .isList(strToBool(pluginEntity.getIsInputList()))
                .build();
        IsOutputList outputList = IsOutputList.builder()
                .toolId(toolId)
                .isList(strToBool(pluginEntity.getIsOutputList()))
                .build();
        List<IsInputList> isInputLists = new ArrayList<>();
        isInputLists.add(isInputList);
        List<IsOutputList> outputLists = new ArrayList<>();
        outputLists.add(outputList);

        pluginDTO.setToolRequestInfo(buildRequestInfoOld(pluginEntity, toolInfo, toolId));
        pluginDTO.setToolInputSchemaList(fillInHeaders(pluginEntity.getInputSchema(), pluginEntity.getRequestInfo()));
        pluginDTO.setToolOutputSchemaList(toolOutputSchemaList);
        pluginDTO.setToolIntfTypeList(toolIntfTypes);
        pluginDTO.setToolTestStatusList(toolTestStatusList);
        pluginDTO.setIsInputList(isInputLists);
        pluginDTO.setIsOutputList(outputLists);
        pluginDTO.setCallMode(pluginEntity.getCallMode());
        pluginDTO.setIsShare(pluginEntity.getIsShare());
        return pluginDTO;
    }

    /**
     * 插件 dto -> entity
     * @param pluginDTO
     * @return entity
     */
    @Override
    public PluginEntity transformDTOtoNewEntity(PluginDTO pluginDTO) {
        PluginEntity pluginEntity = new PluginEntity();
        BeanUtils.copyProperties(pluginDTO, pluginEntity);
        pluginEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());
        try {
            pluginEntity.setRequestInfo(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getToolRequestInfo()));
            pluginEntity.setInputSchema(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getToolInputSchemaList()));
            pluginEntity.setOutputSchema(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getToolOutputSchemaList()));
            pluginEntity.setIntfType(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getToolIntfTypeList()));
            pluginEntity.setTestStatus(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getToolTestStatusList()));
            pluginEntity.setIsInputList(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getIsInputList()));
            pluginEntity.setIsOutputList(JsonUtils.JSON_MAPPER.writeValueAsString(pluginDTO.getIsOutputList()));
        } catch (JsonProcessingException e) {
            log.error("Failed to Object String to String", e);
            throw new AgentStudioException(StudioError.PARSE_STRING_TO_OBJECT_FAILED);
        }

        return pluginEntity;
    }

    @Override
    public String getLastVersion(String pluginId) {
        return pluginMapper.selectVersionByPluginId(pluginId);
    }

    @Override
    public boolean isInnerType(String resourceId) {
        PluginEntity plugin = pluginMapper.selectByPrimaryKey(resourceId, null);
        if (ObjectUtils.isEmpty(plugin)) {
            return true;
        }
        return Strings.CS.equals(plugin.getType(), ToolType.INNER.type);
    }

    public PluginDTO transformNewEntityToDTO(ToolRequestInfo toolRequestInfo, PluginEntity pluginEntity) {
        log.info("transform new entity to dto!");
        PluginDTO pluginDTO = new PluginDTO();
        BeanUtils.copyProperties(pluginEntity, pluginDTO);

        List<ToolInputSchema> toolInputSchemaList = null;
        List<ToolOutputSchema> toolOutputSchemaList = null;
        List<ToolIntfType> toolToolIntfTypeList = null;
        List<ToolTestStatus> toolTestStatusList = null;
        List<IsInputList> isInputLists = null;
        List<IsOutputList> isOutputLists = null;

        try {
            if (pluginEntity.getInputSchema() != null) {
                toolInputSchemaList = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getInputSchema(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolInputSchema.class));
            }

            if (pluginEntity.getOutputSchema() != null) {
                toolOutputSchemaList = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getOutputSchema(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolOutputSchema.class));
            }

            if (pluginEntity.getIntfType() != null) {
                toolToolIntfTypeList = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getIntfType(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolIntfType.class));
            }

            if (pluginEntity.getTestStatus() != null) {
                toolTestStatusList = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getTestStatus(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, ToolTestStatus.class));
            }

            if (pluginEntity.getIsInputList() != null) {
                isInputLists = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getIsInputList(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, IsInputList.class));
            }

            if (pluginEntity.getIsOutputList() != null) {
                isOutputLists = JsonUtils.JSON_MAPPER.readValue(pluginEntity.getIsOutputList(),
                        JsonUtils.JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, IsOutputList.class));
            }
        } catch (JsonProcessingException e) {
            log.error("Failed to parse String to Object", e);
            throw new AgentStudioException(StudioError.PARSE_STRING_TO_OBJECT_FAILED);
        }

        pluginDTO.setToolRequestInfo(toolRequestInfo);
        pluginDTO.setToolInputSchemaList(toolInputSchemaList);
        pluginDTO.setToolOutputSchemaList(toolOutputSchemaList);
        pluginDTO.setToolIntfTypeList(toolToolIntfTypeList);
        pluginDTO.setToolTestStatusList(toolTestStatusList);
        pluginDTO.setIsInputList(isInputLists);
        pluginDTO.setIsOutputList(isOutputLists);
        return pluginDTO;
    }

    private static boolean strToBool(Object value) {
        if ("1".equals(value) || value instanceof Integer && (Integer)value == 1) {
            return true;
        } else if ("0".equals(value) || value instanceof Integer && (Integer)value == 0) {
            return false;
        }
        throw new IllegalArgumentException("Invalid input");
    }

    private List<ToolInputSchema> fillInHeaders(String inputSchema, String requestInfoStr) {
        RequestInfo requestInfo;
        try {
            JsonNode requestInfojsonNode = JsonUtils.JSON_MAPPER.readTree(
                    ObjectUtils.isEmpty(requestInfoStr) ? "{}" : requestInfoStr);
            requestInfo = JsonUtils.JSON_MAPPER.treeToValue(requestInfojsonNode, RequestInfo.class);
        } catch (JsonProcessingException e) {
            log.error("fillInHeaders parse json failed {}", e.getMessage());
            // 构建InputSchema字段
            ToolInputSchema toolInputSchema = ToolInputSchema.builder()
                    .toolId("0")
                    .inputSchema(inputSchema)
                    .build();
            List<ToolInputSchema> toolInputSchemaList = new ArrayList<>();
            toolInputSchemaList.add(toolInputSchema);
            return toolInputSchemaList;
        }
        return buildInputSchemaForOld(inputSchema, requestInfo.getHeaders());
    }

    private ToolRequestInfo buildRequestInfoOld(PluginEntity pluginEntity, ToolInfo toolInfo, String toolId) {
        log.info("start to build old plugin request info!");
        BasicInfo basicInfo = buildBasicInfoOld(pluginEntity, toolInfo, toolId);
        List<ToolInfo> toolInfoList = new ArrayList<>();
        toolInfoList.add(toolInfo);
        return ToolRequestInfo.builder()
                .basicInfo(basicInfo)
                .toolsInfoList(toolInfoList)
                .build();
    }

    private BasicInfo buildBasicInfoOld(PluginEntity pluginEntity, ToolInfo toolInfo, String toolId) {
        // 构建requestInfo字段，包括BasicInfo和tool_info
        UrlInfo urlInfo = null;
        if (toolInfo.getUrl().contains("{")) {
            urlInfo = parseVariableUrl(toolInfo.getUrl());
        } else {
            urlInfo = parseUrl(toolInfo.getUrl());
        }
        BasicInfo basicInfo = BasicInfo.builder()
                .host(urlInfo.getHost())
                .protocol(urlInfo.getProtocol())
                .path("")
                .build();
        toolInfo.setToolId(toolId);
        toolInfo.setToolChineseName(pluginEntity.getPluginChineseName());
        if (ToolType.INNER.type.equals(pluginEntity.getType())) {
            toolInfo.setToolChineseName(pluginEntity.getPluginDisplayName());
        }
        toolInfo.setToolDisplayName(pluginEntity.getPluginDisplayName());
        toolInfo.setToolDesc(pluginEntity.getPluginDesc());
        toolInfo.setPath(urlInfo.getBasePath());
        return basicInfo;
    }

    public UrlInfo parseVariableUrl(String urlString) {
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

        return UrlInfo.builder()
                .host(hostPart)
                .basePath(basePath)
                .protocol(protocol)
                .build();
    }
}

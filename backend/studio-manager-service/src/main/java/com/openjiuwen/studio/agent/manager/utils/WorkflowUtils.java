/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import static com.openjiuwen.studio.agent.manager.utils.CommonUtil.parseMcpConfigHeaderInfo;

import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TypeEnum;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.Message;
import com.openjiuwen.studio.agent.common.dto.auth.OauthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.PluginIAMAuthInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.WorkflowMessageEntity;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthHisIamConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthIamConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthServiceConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthSgovConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthUserConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.CustomIAMConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.OauthConfig;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.util.CollectionUtils;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Queue;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * workflow解析工具类
 *
 */
@Slf4j
public class WorkflowUtils {

    private static final String GRANT_TYPE = "client_credentials";

    /**
     * 根据节点ID获取节点配置信息
     *
     * @param nodeId 节点ID
     * @param workflowNodes 全部节点配置信息
     * @return nodeId节点配置信息
     */
    public static WorkflowNodeVO getWorkflowNodeID(String nodeId, List<WorkflowNodeVO> workflowNodes) {
        // 节点为空标识工作流结束退出
        if (StringUtils.isEmpty(nodeId)) {
            return null;
        }
        if (!CollectionUtils.isEmpty(workflowNodes)) {
            for (WorkflowNodeVO workflowNode : workflowNodes) {
                if (Strings.CS.equals(nodeId, workflowNode.getId())) {
                    return workflowNode;
                }
            }
        }
        log.error("workflow node id {} does not exist", nodeId);
        throw new AgentStudioException(StudioError.WORKFLOW_NODE_ID_NULL);
    }

    /**
     * 消息转换为WorkflowMessageEntity
     *
     * @param sessionId sessionId
     * @param messages messages
     * @return List<WorkflowMessageEntity>
     */
    public static List<WorkflowMessageEntity> convertMessageToMessageEntity(String sessionId, List<Message> messages) {
        return messages.stream().map(message -> {
            WorkflowMessageEntity workflowMessageEntity = new WorkflowMessageEntity();
            workflowMessageEntity.setMessageId(String.valueOf(UUID.randomUUID()));
            workflowMessageEntity.setRole(message.getRole());
            workflowMessageEntity.setContent(message.getContent());
            workflowMessageEntity.setSessionId(sessionId);
            Date currentTime = new Date(System.currentTimeMillis());
            workflowMessageEntity.setCreatedOn(currentTime);
            workflowMessageEntity.setUpdatedOn(currentTime);
            return workflowMessageEntity;
        }).collect(Collectors.toList());
    }

    /**
     * 类型转换驼峰函数
     *
     * @param type 类型
     * @return String
     */
    public static String formatWorkflowType(String type) {
        // 适配老版本转换空类型
        if (StringUtils.isEmpty(type) || type.toLowerCase(Locale.ENGLISH).startsWith(TypeEnum.FILE.toString())) {
            return TypeEnum.STRING.toString();
        } else {
            return type.toLowerCase(Locale.ENGLISH);
        }
    }

    /**
     * workflow actualType 转换，用于输入节点
     *
     * @param dslFieldType 类型
     * @return String actualType
     */
    public static String formatWorkflowActualType(String dslFieldType) {
        return StringUtils.isEmpty(dslFieldType) ? TypeEnum.STRING.toString()
            : dslFieldType.toLowerCase(Locale.ENGLISH);
    }

    /**
     * 从mcp的配置解析出认证信息
     *
     * @param orgType mcp部署方式
     * @param serverConfig mcp配置
     * @return 认证信息
     */
    public static Object parseAuthInfo(String orgType, String serverConfig, AuthInfo authInfo) {
        if (authInfo != null && authInfo.getScope() != null
                && AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())){
            // 构造oauth config对象，保存到ir文件中
            OauthConfig oauthConfig = new OauthConfig();
            buildOauthConfig(oauthConfig, authInfo);
            oauthConfig.setScope(authInfo.getScope().toString());
            return oauthConfig;
        } else if (authInfo != null && authInfo.getScope() != null
                && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            AuthServiceConfig authServiceConfig = new AuthServiceConfig();
            authServiceConfig.setScope(authInfo.getScope().toString());
            Map<String, String> serviceMap = new HashMap<>();
            authInfo.getAuthKeys().forEach(m -> serviceMap.put(m.getTargetName(), m.getAuthKey()));
            if (authInfo.getDomain() == AuthInfo.DomainEnum.HEADERS) {
                authServiceConfig.setHeaders(serviceMap);
                authServiceConfig.setQuery(new HashMap<>());
            } else {
                authServiceConfig.setQuery(serviceMap);
                authServiceConfig.setHeaders(new HashMap<>());
            }
            return authServiceConfig;
        } else {
            return new HashMap<>();
        }
    }

    /**
     * 解析mcp的请求头信息，处理成对象返回
     * @param orgType mcp 类型
     * @param serverConfig 配置服务信息
     * @return 请求头信息
     */
    public static Object parseHeadersOfServerConfig(String orgType, String serverConfig) {
        if (StringUtils.isEmpty(serverConfig)) {
            return new HashMap<>();
        }
        Map<String, String> headers = parseMcpConfigHeaderInfo(serverConfig);
        headers = headers.entrySet()
                .stream()
                .collect(Collectors.toMap(Map.Entry::getKey, entry -> CryptoUtils.encrypt(entry.getValue())));

        if (headers.isEmpty()) {
            return new HashMap<>();
        }

        AuthServiceConfig authServiceConfig = new AuthServiceConfig();
        authServiceConfig.setScope(AuthInfo.ScopeEnum.SERVICE.toString());
        authServiceConfig.setHeaders(headers);

        authServiceConfig.setCryptMethod("scc");

        return authServiceConfig;
    }

    /**
     * 从url删除query参数
     *
     * @param urlString 原始url
     * @return 删除query参数后的url
     */
    public static String removeQueryParamsFromUrl(String urlString) {
        if (urlString == null || urlString.trim().isEmpty()) {
            return urlString;
        }
        // URL 含环境变量占位符 ${_env.plugin_url_params.VAR} 时跳过 URI 解析，真实地址由运行期解析
        if (urlString.contains("${_env.")) {
            return urlString;
        }
        try {
            URI uri = new URI(urlString);
            // 要移除查询参数，只需在构建新URI时将 query 参数设置为 null
            URI newUri = new URI(uri.getScheme(), uri.getUserInfo(), uri.getHost(), uri.getPort(), uri.getPath(), null,
                // 这里设置为 null，移除了查询参数
                uri.getFragment());
            return newUri.toASCIIString();
        } catch (URISyntaxException e) {
            log.error("remove query params from url failed.", e);
            return urlString;
        }
    }

    /**
     * 从给定的 URL 字符串中提取所有查询参数并返回为一个 Map。
     * 注意：如果一个参数名出现多次，Map 中将存储最后一个出现的值。
     *
     * @param urlString 包含查询参数的 URL 字符串。
     * @return 包含解析出的查询参数的 Map。键和值都经过 URL 解码。
     *         如果 URL 无效、没有查询部分或查询部分为空，则返回一个空的不可变 Map。
     */
    public static Map<String, String> extractQueryParamsFromUrl(String urlString) {
        // 健壮性检查：如果 URL 是 null 或空白，直接返回空 Map
        if (urlString == null || urlString.trim().isEmpty()) {
            return Collections.emptyMap();
        }
        // URL 含环境变量占位符时跳过 URI 解析，真实地址由运行期解析
        if (urlString.contains("${_env.")) {
            return Collections.emptyMap();
        }
        try {
            // 使用 URI 类来解析 URL，因为它更擅长处理结构上的验证和分解
            URI uri = new URI(urlString.trim());
            String query = uri.getQuery();
            // 如果没有查询部分，也返回空 Map
            if (query == null || query.isEmpty()) {
                return Collections.emptyMap();
            }
            // 使用 HashMap 来存储参数
            Map<String, String> queryParams = new HashMap<>();
            // 按 '&' 分割每个参数对
            String[] pairs = query.split("&");
            for (String pair : pairs) {
                if (pair.isEmpty()) {
                    continue; // 跳过空的参数对 (例如 "param&&param2")
                }

                int idx = pair.indexOf('=');
                String key;
                String value;
                if (idx > 0) { // 找到了 '='
                    key = pair.substring(0, idx);
                    value = pair.substring(idx + 1);
                } else { // 没有 '='，例如 "?param"
                    key = pair;
                    value = ""; // 值为空字符串
                }
                // 对键和值进行 URL 解码
                // StandardCharsets.UTF_8 是现代 Java 中推荐的字符集常量
                String decodedKey = URLDecoder.decode(key, StandardCharsets.UTF_8);
                String decodedValue = URLDecoder.decode(value, StandardCharsets.UTF_8);
                queryParams.put(decodedKey, decodedValue);
            }
            return queryParams;
        } catch (URISyntaxException e) {
            log.error("extract query params from url failed.", e);
            return Collections.emptyMap();
        }
    }

    /**
     * 解析AuthInfo转换为ir定义
     *
     * @param authInfo 鉴权信息
     * @return Object
     */
    public static Object parseAuthInfo(AuthInfo authInfo) {
        if (authInfo != null && authInfo.getScope() != null && AuthInfo.ScopeEnum.USER.equals(authInfo.getScope())) {
            AuthUserConfig authUserConfig = new AuthUserConfig();
            authUserConfig.setScope(authInfo.getScope().toString());
            AuthUserConfig.Info source = new AuthUserConfig.Info();
            source.setDomain("headers");
            source.setAuthKeys(
                authInfo.getAuthKeys().stream().map(AuthKeyInfo::getSourceName).collect(Collectors.toList()));
            AuthUserConfig.Info target = new AuthUserConfig.Info();
            target.setDomain(authInfo.getDomain().toString().toLowerCase(Locale.ENGLISH));
            target.setAuthKeys(
                authInfo.getAuthKeys().stream().map(AuthKeyInfo::getTargetName).collect(Collectors.toList()));
            authUserConfig.setSource(source);
            authUserConfig.setTarget(target);
            return authUserConfig;
        } else if (authInfo != null && authInfo.getScope() != null
            && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
            AuthServiceConfig authServiceConfig = new AuthServiceConfig();
            authServiceConfig.setScope(authInfo.getScope().toString());
            Map<String, String> serviceMap = new HashMap<>();
            authInfo.getAuthKeys().forEach(m -> serviceMap.put(m.getTargetName(), m.getAuthKey()));
            if (authInfo.getDomain() == AuthInfo.DomainEnum.HEADERS) {
                authServiceConfig.setHeaders(serviceMap);
                authServiceConfig.setQuery(new HashMap<>());
            } else {
                authServiceConfig.setQuery(serviceMap);
                authServiceConfig.setHeaders(new HashMap<>());
            }
            return authServiceConfig;
        } else if (authInfo != null && authInfo.getScope() != null
            && AuthInfo.ScopeEnum.IAM.equals(authInfo.getScope())) {
            AuthIamConfig authIamConfig = new AuthIamConfig();
            authIamConfig.setScope(authInfo.getScope().toString());
            return authIamConfig;
        } else if (authInfo != null && authInfo.getScope() != null
            && AuthInfo.ScopeEnum.HIS_IAM.equals(authInfo.getScope())) {
            AuthHisIamConfig authHisIamConfig = new AuthHisIamConfig();

            authHisIamConfig.setUrl(authInfo.getHisIamInfo().getIamUrl());
            authHisIamConfig.setEnterprise(authInfo.getHisIamInfo().getIamEnterprise());
            authHisIamConfig.setAccount(authInfo.getHisIamInfo().getIamAccount());
            authHisIamConfig.setSecret(authInfo.getHisIamInfo().getIamSecret());
            authHisIamConfig.setProject(authInfo.getHisIamInfo().getIamProject());
            authHisIamConfig.setScope(authInfo.getScope().toString());
            return authHisIamConfig;
        } else if (authInfo != null && authInfo.getScope() != null
            && AuthInfo.ScopeEnum.SGOV.equals(authInfo.getScope())) {
            AuthSgovConfig authSgovConfig = new AuthSgovConfig();

            authSgovConfig.setUrl(authInfo.getHisSgov().getSgovUrl());
            authSgovConfig.setAppId(authInfo.getHisSgov().getAppId());
            authSgovConfig.setCredential(authInfo.getHisSgov().getCredential());
            authSgovConfig.setScope(authInfo.getScope().toString());
            return authSgovConfig;
        } else if (authInfo != null && authInfo.getScope() != null
            && AuthInfo.ScopeEnum.CUSTOM_IAM.equals(authInfo.getScope())) {
            // 构造iam config对象,保存到ir文件中
            CustomIAMConfig customIAMConfig = new CustomIAMConfig();
            buildAuthIamConfig(customIAMConfig, authInfo);
            customIAMConfig.setScope(authInfo.getScope().toString());
            return customIAMConfig;
        } else {
            return new HashMap<>();
        }
    }

    /**
     * 解析http节点url
     *
     * @param configs http节点配置
     * @return 解析的url
     */
    public static String parseHttpEndpoint(Map<String, Object> configs) {
        if (configs != null && configs.get(CommonConstant.Http.ENDPOINT) != null) {
            try {
                URI baseUri = new URI(configs.get(CommonConstant.Http.ENDPOINT).toString());
                return baseUri.toString();
            } catch (URISyntaxException e) {
                log.error("parse http url failed!");
                return StringUtils.EMPTY;
            }
        } else {
            return StringUtils.EMPTY;
        }
    }

    /**
     * 获取工作流中的游离节点(开始节点不可达的节点)
     *
     * @param workflowVo 工作流DSL
     * @return 游离节点id列表
     */
    public static Set<String> getFreeNodes(WorkflowVO workflowVo) {
        // 获取节点邻接表，用于得到与开始节点直接/间接相连的节点
        Map<String,
            WorkflowNodeVO> nodeMap = workflowVo.getNodes()
                .stream()
                .collect(Collectors.toMap(WorkflowNodeVO::getId, workflowNodeVO -> workflowNodeVO));

        Map<String, List<String>> edgeMap = new HashMap<>();
        for (WorkflowEdgeVO edge : workflowVo.getEdges()) {
            List<String> targets = edgeMap.getOrDefault(edge.getSource(), new ArrayList<>());

            // 循环节点内的节点也添加到邻接表
            WorkflowNodeVO node = nodeMap.get(edge.getTarget());
            if (node != null && NodeType.LOOP.getType().equals(node.getType())) {
                Map<String, Object> configs = node.getConfigs();
                if (configs != null && configs.containsKey(CommonConstant.Workflow.LOOP_BODY)) {
                    List<String> loopBodyIds = JsonUtils.objectToClass(configs.get(CommonConstant.Workflow.LOOP_BODY));
                    if (loopBodyIds != null) {
                        loopBodyIds.add(node.getId() + CommonConstant.LOOP_INPUT);
                        loopBodyIds.add(node.getId() + CommonConstant.LOOP_OUTPUT);
                        targets.addAll(loopBodyIds);
                    }
                }
            }
            targets.add(edge.getTarget());
            edgeMap.put(edge.getSource(), targets);
        }

        // 遍历获取所有与开始节点直接/间接相连的节点
        Set<String> visit = new HashSet<>();
        visit.add(CommonConstant.Workflow.NODE_START);
        getNodesFromMap(edgeMap, visit);
        visit.add(CommonConstant.Workflow.NODE_END);

        // 过滤得到游离节点
        return workflowVo.getNodes()
            .stream()
            .map(WorkflowNodeVO::getId)
            .filter(id -> !visit.contains(id))
            .collect(Collectors.toSet());
    }

    /**
     * 根据邻接表提取非游离节点
     *
     * @param edgeMap edgeMap
     */
    public static void getNodesFromMap(Map<String, List<String>> edgeMap, Set<String> visit) {
        Queue<String> queue = new LinkedList<>();
        queue.add(CommonConstant.Workflow.NODE_START);
        while (!queue.isEmpty()) {
            String node = queue.poll();
            List<String> targets = edgeMap.get(node);
            if (targets == null) {
                continue;
            }

            // 将未访问过的节点添加到已访问集合和队列中
            for (String target : targets) {
                if (visit.add(target)) {
                    queue.add(target);
                }
            }
        }
    }

    public static void buildAuthIamConfig(CustomIAMConfig iamConfig, AuthInfo authInfo) {
        PluginIAMAuthInfo customIamCredentials = authInfo.getCustomIamCredentials();
        if (Objects.isNull(customIamCredentials)) {
            return;
        }

        iamConfig.setIamProject(customIamCredentials.getIamProject());
        iamConfig.setIamPassword(customIamCredentials.getIamPassword());
        iamConfig.setIamDomain(customIamCredentials.getIamDomain());
        iamConfig.setIamUrl(customIamCredentials.getIamUrl());
        iamConfig.setIamUser(customIamCredentials.getIamUser());
        iamConfig.setIamAK(customIamCredentials.getIamAk());
        iamConfig.setIamSK(customIamCredentials.getIamSk());
    }

    /**
     * 构建oauth鉴权信息
     * @param oauthConfig ir中oauth配置
     * @param authInfo 鉴权信息
     */
    public static void buildOauthConfig(OauthConfig oauthConfig, AuthInfo authInfo) {
        log.info("start to create oauth config for ir!");
        OauthInfo oauth = authInfo.getCustomOauth();
        if (Objects.isNull(oauth)) {
            return;
        }

        // oauthScope为可选字段
        oauthConfig.setEndpointUrl(oauth.getEndpointUrl());
        oauthConfig.setGrantType(GRANT_TYPE);
        oauthConfig.setClientId(oauth.getClientId());
        oauthConfig.setClientSecret(oauth.getClientSecret());
        if (oauth.getScope() != null) {
            oauthConfig.setOauthScope(oauth.getScope());
        }
    }
}

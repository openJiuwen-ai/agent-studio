/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.McpTransferServiceDefinition;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * FEAT-134 MCP 迁移配置安全清理器（导出投影 + 导入安全校验双向共用）。
 *
 * 设计依据 L2 §2.3.1：平台鉴权字段及结构化配置中的凭据槽位是安全保证的适用面；
 * 已知凭据值的二次扫描覆盖导出所有字符串；自由文本中的隐含秘密是剩余风险。
 * 本类不做数据库写入。
 */
@Component
public class McpTransferSanitizer {

    /** 标准配置节点允许的键（mcpServers 外壳内每个服务节点）。 */
    private static final Set<String> ALLOWED_NODE_KEYS = Set.of("url", "command", "args", "headers", "env");

    /** 迁移安全契约禁止出现在文件中的顶层鉴权字段（统一小写匹配）。 */
    private static final Set<String> FORBIDDEN_CREDENTIAL_KEYS =
        Set.of("auth", "authinfo", "auth_info", "customoauth", "custom_oauth", "iam", "credentials", "token",
            "temptoken", "temp_token", "secret", "password", "apikey", "api_key");

    /** 工具 schema 中移除的可携带样例值的字段。 */
    private static final Set<String> TOOL_SCHEMA_REMOVED_KEYS = Set.of("default", "example", "examples");

    /** 已知敏感头名（仅用于 requiresAuth 推断；清理策略为「全部头值剔除」，不依赖黑名单）。 */
    private static final Set<String> KNOWN_SENSITIVE_HEADERS =
        Set.of("authorization", "cookie", "x-hw-id", "x-hw-appkey", "x-auth-token");

    /**
     * 平台支持的唯一占位符形态：整串 URL 恰为一个环境变量占位符
     * （创建侧契约：仅整串，不支持内嵌）。含占位符但非此形态的 URL
     * 一律按普通 URL 走完整校验（防内嵌形态绕过 userinfo/query 检查）。
     */
    private static final java.util.regex.Pattern WHOLE_FORM_PLACEHOLDER =
        java.util.regex.Pattern.compile("^\\$\\{_env\\.plugin_url_params\\.[A-Za-z0-9_-]+\\}$");

    public static boolean isWholeFormEnvPlaceholder(String url) {
        return url != null && WHOLE_FORM_PLACEHOLDER.matcher(url).matches();
    }

    /**
     * 导出侧：清理服务定义，输出安全投影 + 记录被清理路径。
     * 输入为已解密的 serverConfig（Map 形态）与源工具快照。
     */
    public SanitizeResult sanitizeForExport(String url, Map<String, Object> serverConfig,
        List<Map<String, Object>> toolsSnapshot, boolean hasAuthInfo) {
        SanitizeResult result = new SanitizeResult();
        result.url = sanitizeUrlForExport(url, result.redactedPaths, result.pendingPaths);
        if (serverConfig != null) {
            result.serverConfig = sanitizeServerConfig(serverConfig, result.redactedPaths, result.pendingPaths);
        }
        result.toolsSnapshot = sanitizeToolsSnapshot(toolsSnapshot, result.redactedPaths);
        result.requiresAuth = hasAuthInfo || !result.pendingPaths.isEmpty()
            || containsKnownSensitiveHeader(serverConfig);
        return result;
    }

    /**
     * 导入侧：安全契约校验。文件携带鉴权字段、未清理的头值/env 值/query 值时拒绝
     * （安全清理不能只在导出端执行——不借导入接口接收或保存新凭据）。
     */
    public void validateImportSafety(McpTransferServiceDefinition definition) {
        Map<String, Object> serverConfig = definition.getServerConfig();
        if (serverConfig != null) {
            rejectCredentialKeys(serverConfig, "", false);
        }
        // 仅整串占位符形态跳过校验（解析后、出站前由取数链路校验）；
        // 内嵌占位符（如 https://${_env.x}?token=secret）按普通 URL 全量校验
        String url = definition.getUrl();
        if (StringUtils.isNotBlank(url) && !isWholeFormEnvPlaceholder(url)) {
            validateUrlSafety(url);
        }
        if (serverConfig != null) {
            Object mcpServers = serverConfig.get("mcpServers");
            if (mcpServers instanceof Map<?, ?> servers) {
                if (servers.size() != 1) {
                    throw fieldInvalid("server_config.mcpServers must contain exactly one service node");
                }
                for (Map.Entry<?, ?> entry : servers.entrySet()) {
                    if (!(entry.getValue() instanceof Map<?, ?>)) {
                        throw fieldInvalid("mcpServers node must be an object");
                    }
                    validateNodeSafety((Map<String, Object>) entry.getValue(),
                        "/server_config/mcpServers/" + entry.getKey());
                }
            } else {
                throw fieldInvalid("server_config.mcpServers missing or invalid");
            }
        }
    }

    private void validateNodeSafety(Map<String, Object> node, String basePath) {
        for (Map.Entry<String, Object> entry : node.entrySet()) {
            String key = entry.getKey();
            if (!ALLOWED_NODE_KEYS.contains(key)) {
                throw unsafe("unknown config key rejected: " + basePath + "/" + key);
            }
            // 严格类型校验（fail-closed）：类型不匹配一律拒绝，不放行待运行期再炸
            if ("url".equals(key)) {
                if (!(entry.getValue() instanceof String)) {
                    throw unsafe("non-string url value rejected: " + basePath + "/url");
                }
                // 节点 url 与顶层 url 同规则；仅整串占位符形态跳过（内嵌形态全量校验）
                String nodeUrl = (String) entry.getValue();
                if (StringUtils.isNotBlank(nodeUrl) && !isWholeFormEnvPlaceholder(nodeUrl)) {
                    validateUrlSafety(nodeUrl);
                }
            } else if ("headers".equals(key)) {
                if (!(entry.getValue() instanceof Map<?, ?> headers)) {
                    throw unsafe("non-object headers rejected: " + basePath + "/headers");
                }
                for (Map.Entry<?, ?> h : headers.entrySet()) {
                    if (h.getValue() != null && !"".equals(h.getValue())) {
                        throw unsafe("non-empty header value rejected: " + basePath + "/headers/" + h.getKey());
                    }
                }
            } else if ("env".equals(key)) {
                if (!(entry.getValue() instanceof Map<?, ?> env)) {
                    throw unsafe("non-object env rejected: " + basePath + "/env");
                }
                for (Map.Entry<?, ?> e : env.entrySet()) {
                    if (e.getValue() != null && !"".equals(e.getValue())) {
                        throw unsafe("non-empty env value rejected: " + basePath + "/env/" + e.getKey());
                    }
                }
            } else if ("args".equals(key)) {
                if (!(entry.getValue() instanceof List<?> args)) {
                    throw unsafe("non-list args rejected: " + basePath + "/args");
                }
                for (Object arg : args) {
                    // 非字符串元素（如内嵌对象）不属于启动器参数合法形态，拒绝
                    if (!(arg instanceof String s)) {
                        throw unsafe("non-string args element rejected: " + basePath + "/args");
                    }
                    if (s.startsWith("-") && !isKnownLauncherFlag(s)) {
                        throw unsafe("unknown launcher flag rejected: " + basePath + "/args/" + s);
                    }
                }
            } else if ("command".equals(key)) {
                if (!(entry.getValue() instanceof String)) {
                    throw unsafe("non-string command value rejected: " + basePath + "/command");
                }
            }
        }
    }

    /**
     * 递归拒绝凭据键——但跳过标准配置节点的值区域（env/headers/args 的键名是
     * 合法变量名如 API_KEY，值已由 validateNodeSafety 单独校验为空/非空）。
     * List 元素同样递归（args:[{token:...}] 这类嵌套对象不能绕过键名检查）。
     */
    private void rejectCredentialKeys(Map<String, Object> map, String path, boolean insideStandardNode) {
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            String lowerKey = StringUtils.lowerCase(entry.getKey());
            // 标准节点内的键名（env 变量名/headers 头名/args 参数名）不按凭据字段名拒绝
            if (!insideStandardNode) {
                String normalizedKey = lowerKey.replace("-", "").replace("_", "");
                if (FORBIDDEN_CREDENTIAL_KEYS.contains(lowerKey)
                    || FORBIDDEN_CREDENTIAL_KEYS.contains(normalizedKey)
                    || normalizedKey.contains("oauth") || normalizedKey.contains("credential")) {
                    throw unsafe("credential field rejected in file: " + (path.isEmpty() ? "/" : path) + "/"
                        + entry.getKey());
                }
            }
            // 递归时：进入 mcpServers 节点标记为标准区域（服务名是任意字符串，
            // 不能按凭据字段名拒绝——注意 lowerKey 已小写，须与小写常量比较）
            boolean childIsNode = "mcpservers".equals(lowerKey) || ALLOWED_NODE_KEYS.contains(lowerKey);
            if (entry.getValue() instanceof Map<?, ?> child) {
                rejectCredentialKeys((Map<String, Object>) child, path + "/" + entry.getKey(), childIsNode);
            } else if (entry.getValue() instanceof List<?> list) {
                // List 元素继承当前区域标记：标准节点内（args）属值区域；顶层未知
                // 列表的内嵌对象不在豁免区，凭据键名照常拒绝
                for (int i = 0; i < list.size(); i++) {
                    if (list.get(i) instanceof Map<?, ?> element) {
                        rejectCredentialKeys((Map<String, Object>) element,
                            path + "/" + entry.getKey() + "/" + i, insideStandardNode);
                    }
                }
            }
        }
    }

    private void validateUrlSafety(String url) {
        try {
            URI uri = new URI(url);
            if (uri.getRawUserInfo() != null) {
                throw unsafe("URL userinfo rejected");
            }
            if (uri.getRawQuery() != null && !uri.getRawQuery().isEmpty()) {
                for (String pair : uri.getRawQuery().split("&")) {
                    int eq = pair.indexOf('=');
                    if (eq >= 0 && eq < pair.length() - 1) {
                        throw unsafe("non-empty URL query value rejected");
                    }
                }
            }
        } catch (URISyntaxException e) {
            throw fieldInvalid("url is not a valid URI");
        }
    }

    private String sanitizeUrlForExport(String url, List<String> redacted, List<String> pending) {
        if (StringUtils.isBlank(url)) {
            return url;
        }
        // 仅整串占位符原样保留（目标环境解析）；内嵌占位符按普通 URL 清洗
        // （非占位部分的 userinfo/query 照常剔除，防借占位符绕过导出清洗）
        if (isWholeFormEnvPlaceholder(url)) {
            return url;
        }
        try {
            URI uri = new URI(url);
            String safe = rebuildUri(uri, redacted, pending);
            return safe;
        } catch (URISyntaxException e) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "url is not a valid URI and cannot be safely exported");
        }
    }

    private String rebuildUri(URI uri, List<String> redacted, List<String> pending) {
        try {
            String query = null;
            String rawQuery = uri.getRawQuery();
            if (rawQuery != null && !rawQuery.isEmpty()) {
                List<String> keptParams = new ArrayList<>();
                for (String pair : rawQuery.split("&")) {
                    int eq = pair.indexOf('=');
                    String name = eq >= 0 ? pair.substring(0, eq) : pair;
                    keptParams.add(name + "=");
                    pending.add("/url/query/" + name);
                }
                query = String.join("&", keptParams);
            }
            if (uri.getRawUserInfo() != null) {
                redacted.add("/url/userinfo");
            }
            URI cleaned = new URI(uri.getScheme(), null, uri.getHost(), uri.getPort(),
                uri.getRawPath(), query, null);
            if (uri.getRawFragment() != null) {
                redacted.add("/url/fragment");
            }
            return cleaned.toString();
        } catch (URISyntaxException e) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "url cannot be safely projected");
        }
    }

    private Map<String, Object> sanitizeServerConfig(Map<String, Object> serverConfig, List<String> redacted,
        List<String> pending) {
        Map<String, Object> output = new LinkedHashMap<>();
        output.put("mcpServers", new LinkedHashMap<String, Object>());
        Object mcpServers = serverConfig.get("mcpServers");
        if (mcpServers instanceof Map<?, ?> servers) {
            Map<String, Object> serversOut = (Map<String, Object>) output.get("mcpServers");
            for (Map.Entry<?, ?> entry : servers.entrySet()) {
                if (entry.getValue() instanceof Map<?, ?>) {
                    serversOut.put(String.valueOf(entry.getKey()),
                        sanitizeNode((Map<String, Object>) entry.getValue(),
                            "/server_config/mcpServers/" + entry.getKey(), redacted, pending));
                }
            }
        }
        return output;
    }

    private Map<String, Object> sanitizeNode(Map<String, Object> node, String basePath, List<String> redacted,
        List<String> pending) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : node.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            if ("headers".equals(key) && value instanceof Map<?, ?>) {
                Map<String, Object> emptyHeaders = new LinkedHashMap<>();
                for (Map.Entry<?, ?> h : ((Map<?, ?>) value).entrySet()) {
                    String headerName = String.valueOf(h.getKey());
                    if (h.getValue() != null && !"".equals(h.getValue())) {
                        redacted.add(basePath + "/headers/" + headerName);
                        if (KNOWN_SENSITIVE_HEADERS.contains(StringUtils.lowerCase(headerName))) {
                            pending.add(basePath + "/headers/" + headerName);
                        }
                    }
                    emptyHeaders.put(headerName, "");
                }
                out.put("headers", emptyHeaders);
            } else if ("env".equals(key) && value instanceof Map<?, ?>) {
                Map<String, Object> envOut = new LinkedHashMap<>();
                for (Map.Entry<?, ?> e : ((Map<?, ?>) value).entrySet()) {
                    if (e.getValue() != null && !"".equals(e.getValue())) {
                        redacted.add(basePath + "/env/" + e.getKey());
                    }
                    envOut.put(String.valueOf(e.getKey()), null);
                }
                out.put("env", envOut);
            } else if ("args".equals(key) && value instanceof List<?> args) {
                out.put("args", sanitizeArgs(args, basePath, redacted, pending));
            } else if ("url".equals(key) && value instanceof String s) {
                out.put("url", sanitizeUrlForExport(s, redacted, pending));
            } else if (ALLOWED_NODE_KEYS.contains(key)) {
                out.put(key, value);
            }
            // 未知键不透传（L2：无法安全投影的未知结构拒绝——此处节点级未知键直接丢弃并记录）
            else if (key != null) {
                redacted.add(basePath + "/" + key);
            }
        }
        return out;
    }

    private List<Object> sanitizeArgs(List<?> args, String basePath, List<String> redacted,
        List<String> pending) {
        List<Object> out = new ArrayList<>();
        boolean packageSeen = false;
        for (Object arg : args) {
            if (!(arg instanceof String s)) {
                redacted.add(basePath + "/args");
                continue;
            }
            if (isKnownLauncherFlag(s)) {
                out.add(s);
            } else if (!packageSeen && !s.startsWith("-")) {
                out.add(s);
                packageSeen = true;
            } else {
                redacted.add(basePath + "/args/" + s);
                pending.add(basePath + "/args/" + s);
            }
        }
        return out;
    }

    private boolean isKnownLauncherFlag(String s) {
        return "-y".equals(s) || "--yes".equals(s);
    }

    private List<Map<String, Object>> sanitizeToolsSnapshot(List<Map<String, Object>> tools, List<String> redacted) {
        if (tools == null) {
            return List.of();
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> tool : tools) {
            out.add(sanitizeTool(tool, redacted));
        }
        return out;
    }

    private Map<String, Object> sanitizeTool(Map<String, Object> tool, List<String> redacted) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : tool.entrySet()) {
            if (TOOL_SCHEMA_REMOVED_KEYS.contains(entry.getKey())) {
                redacted.add("/tools/" + entry.getKey());
                continue;
            }
            if (entry.getValue() instanceof Map<?, ?> child) {
                out.put(entry.getKey(), sanitizeTool((Map<String, Object>) child, redacted));
            } else if (entry.getValue() instanceof List<?> list) {
                out.put(entry.getKey(), sanitizeToolList(list, redacted));
            } else {
                out.put(entry.getKey(), entry.getValue());
            }
        }
        return out;
    }

    private List<Object> sanitizeToolList(List<?> list, List<String> redacted) {
        List<Object> out = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?>) {
                out.add(sanitizeTool((Map<String, Object>) item, redacted));
            } else {
                out.add(item);
            }
        }
        return out;
    }

    private boolean containsKnownSensitiveHeader(Map<String, Object> serverConfig) {
        if (serverConfig == null) {
            return false;
        }
        Object mcpServers = serverConfig.get("mcpServers");
        if (mcpServers instanceof Map<?, ?> servers) {
            for (Map.Entry<?, ?> entry : servers.entrySet()) {
                if (entry.getValue() instanceof Map<?, ?> node) {
                    Object headers = ((Map<?, ?>) node).get("headers");
                    if (headers instanceof Map<?, ?> headerMap) {
                        for (Map.Entry<?, ?> h : headerMap.entrySet()) {
                            if (KNOWN_SENSITIVE_HEADERS.contains(StringUtils.lowerCase(String.valueOf(h.getKey())))
                                && h.getValue() != null && !"".equals(h.getValue())) {
                                return true;
                            }
                        }
                    }
                }
            }
        }
        return false;
    }

    /**
     * 导出端已知凭据值二次扫描：命中即拒绝（不把已知秘密写入迁移文件）。
     */
    public void scanForKnownSecrets(String serializedFile, List<String> knownSecretValues) {
        for (String secret : knownSecretValues) {
            if (StringUtils.isNotBlank(secret) && secret.length() >= 6 && serializedFile.contains(secret)) {
                throw unsafe("known credential value detected in export output; export rejected");
            }
        }
    }

    private AgentStudioException unsafe(String reason) {
        return new AgentStudioException(StudioError.MCP_TRANSFER_UNSAFE_CONFIG, reason);
    }

    private AgentStudioException fieldInvalid(String reason) {
        return new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID, reason);
    }

    /**
     * 清理结果（导出侧）：安全投影 + 清理路径 + 待补配路径 + 是否需要鉴权提示。
     */
    public static class SanitizeResult {
        public String url;
        public Map<String, Object> serverConfig;
        public List<Map<String, Object>> toolsSnapshot;
        public final List<String> redactedPaths = new ArrayList<>();
        public final List<String> pendingPaths = new ArrayList<>();
        public boolean requiresAuth;
    }
}

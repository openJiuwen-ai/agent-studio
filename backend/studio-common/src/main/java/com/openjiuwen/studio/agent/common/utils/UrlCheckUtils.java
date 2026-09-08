/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 功能描述
 *
 */
@Component
@Slf4j
public class UrlCheckUtils {
    /**
     * 匹配任意 ``${...}`` 占位符（含大括号），用于逐一校验。
     */
    private static final Pattern PLACEHOLDER_PATTERN = Pattern.compile("\\$\\{([^}]*)\\}");

    /**
     * 合法的环境变量占位符：``${_env.plugin_url_params.VAR}``（子串匹配）。
     * 与 Python ``env_resolver.py`` / ``logging_context.py:47`` 同源，跨环境迁移模型 apiUrl 占位符以此为准。
     * 变量名 VAR 必须匹配环境变量配置侧命名正则：``[a-zA-Z_$][a-zA-Z0-9_$]*``（与前端
     * ``config-env-variable.component.ts:103`` 的 ``NAME_PATTERN`` 对齐），确保占位符里的变量名
     * 能在环境管理页建成同名变量。
     */
    private static final Pattern VALID_ENV_PLACEHOLDER =
        Pattern.compile("\\$\\{_env\\.plugin_url_params\\.([a-zA-Z_$][a-zA-Z0-9_$]*)\\}");

    /**
     * 合法的环境变量占位符：整串必须是 ``${_env.plugin_url_params.VAR}``（整串匹配，anchored）。
     * 用于 checkUrl 判断"整个 URL 就是一个占位符、运行期才解析"的场景，此类值跳过 URI/IP 校验。
     */
    private static final Pattern VALID_ENV_PLACEHOLDER_FULL =
        Pattern.compile("^\\$\\{_env\\.plugin_url_params\\.([a-zA-Z_$][a-zA-Z0-9_$]*)\\}$");

    /**
     * 用户点击 {} 按钮后未填变量名的空占位符字符串，与前端 USER_EMPTY_PLACEHOLDER 同源。
     * 保存时原样入库，等价于"尚未配置占位符"，跳过 URI/IP 校验。
     */
    private static final String USER_EMPTY_PLACEHOLDER = "{}";

    @Value("${tool.url.enable-check}")
    private boolean enableUrlCheck;

    @Value("${tool.url.black-list}")
    private String toolUrlBlackListStr;

    @Value("${tool.url.white-list}")
    private String toolUrlWhiteListStr;

    private List<String> toolUrlBlackList;

    private List<String> toolUrlWhiteList;

    @PostConstruct
    private void init() {
        toolUrlBlackList = StringUtils.isBlank(toolUrlBlackListStr) ? new ArrayList<>()
                : Arrays.asList(toolUrlBlackListStr.split(","));
        toolUrlWhiteList = StringUtils.isBlank(toolUrlWhiteListStr) ? new ArrayList<>()
                : Arrays.asList(toolUrlWhiteListStr.split(","));
    }

    /**
     * 校验 apiUrl 语法是否合法。
     *
     * <p>与前端创建模型的校验严格对齐（{@code USER_URL_PATTERN = /^https?:\/\/[^{}\s]+$/i} +
     * {@code USER_ENV_PLACEHOLDER = /^{\{[a-zA-Z_$][a-zA-Z0-9_$]*\}$/}）：
     * <ul>
     *   <li>整串为合法占位符（{@code ${_env.plugin_url_params.VAR}} 或 {@code {}}）——运行期由
     *       Python {@code env_resolver.py} 解析为真实 URL，直接放行；</li>
     *   <li>否则必须是 http(s) 绝对 URL，且 URL 任何位置都不得包含 {@code {/}} 字符
     *       （禁止 URL 中间嵌占位符，如 {@code https://${VAR}/v1} 这种"半占位符"写法创建页就拒绝，
     *       导入侧保持一致）。</li>
     * </ul>
     *
     * <p>与 {@link #checkUrl(String, String)} 的区别：checkUrl 是 SSRF 防护（黑名单/白名单/内网 IP 拦截），
     * 受 {@code tool.url.enable-check} 开关控制，默认关闭；本方法是纯语法校验，始终执行。
     * 错误抛 {@link StudioError#INVALID_URL}。
     */
    public void validateUrlSyntax(String url) {
        if (StringUtils.isEmpty(url)) {
            return;
        }
        String trimmed = url.trim();
        // 整串占位符形态：
        //   - {}（用户空占位）
        //   - ${_env.plugin_url_params.VAR}（合法后端格式）
        //   - ${...}（整串但形态非法，如 ${evil.var}）——作为"占位符形状"放行，由 validateEnvVarPlaceholders 负责
        //     判语法非法，保持"URL 语法 / 占位符语法"两标志独立（apiUrlValid=true 仅代表非 URL 结构错误）。
        // 整串 {VAR} 用户形态（非后端存储格式）也视为占位符形状放行，避免误判为 URL 错误。
        if (isFullPlaceholder(trimmed) || isFullPlaceholderShaped(trimmed)) {
            return;
        }
        // 非整串占位符：URL 任何位置含 { 或 } 一律拒绝（禁止内联占位符），与前端 USER_URL_PATTERN 的 [^{}\s]+ 对齐。
        if (trimmed.indexOf('{') >= 0 || trimmed.indexOf('}') >= 0) {
            log.error("URL must not contain inline placeholder/braces (only whole-string placeholder allowed): [{}]", url);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        URI parsedUri;
        try {
            parsedUri = new URI(trimmed);
        } catch (URISyntaxException e) {
            log.error("Invalid URL syntax [{}]", url, e);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        String scheme = parsedUri.getScheme();
        if (scheme == null || (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme))) {
            log.error("URL scheme must be http or https: [{}]", url);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        if (StringUtils.isEmpty(parsedUri.getHost())) {
            log.error("URL has no host: [{}]", url);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
    }

    /**
     * 判断字符串是否"形如整串占位符"——以 {@code ${} 或 {@code {}} 包裹且内容不含花括号。
     * 用于在 validateUrlSyntax 中放行整串占位符（合法或非法形态都交给 validateEnvVarPlaceholders 判定），
     * 保持"URL 结构错误"与"占位符语法错误"两标志独立。
     */
    private boolean isFullPlaceholderShaped(String s) {
        if (s == null || s.length() < 2) {
            return false;
        }
        // ${...}
        if (s.startsWith("${") && s.endsWith("}")) {
            String inner = s.substring(2, s.length() - 1);
            return inner.indexOf('{') < 0 && inner.indexOf('}') < 0;
        }
        // {...}（用户形态 {VAR}）
        if (s.startsWith("{") && s.endsWith("}")) {
            String inner = s.substring(1, s.length() - 1);
            return inner.indexOf('{') < 0 && inner.indexOf('}') < 0;
        }
        return false;
    }

    public void checkUrl(String projectId, String url) {
        log.info("start to checkUrl {}", url);
        // 未开启检查（默认开启），返回
        if (!enableUrlCheck || StringUtils.isEmpty(url)) {
            log.info("not check url");
            return;
        }
        String trimmed = url.trim();
        // 整串就是一个合法占位符（${_env.plugin_url_params.VAR} 或 {}），运行期才解析，跳过 URI/IP 校验。
        // 注意：这里只放通"整串占位符"的情况。若 URL 中间嵌 ${...} 或含裸 { / }，
        // 将走下面的 URI 解析，因未转义花括号触发 URISyntaxException → INVALID_URL，避免 SSRF/绕过。
        if (isFullPlaceholder(trimmed)) {
            log.info("url is a full placeholder, skip URI/IP check");
            return;
        }

        URI parsedUri;
        try {
            parsedUri = new URI(trimmed);
        } catch (URISyntaxException e) {
            log.error("Fail to parse url [{}]", url, e);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }
        String host = parsedUri.getHost();

        // 1. 检查黑名单
        if (toolUrlBlackList.contains(host)) {
            log.error("URL is blocked by blacklist [{}]", url);
            throw new AgentStudioException(StudioError.INVALID_URL);
        }

        // 2. 检查白名单（白名单优先级高于其他规则）
        if (toolUrlWhiteList.contains(host)) {
            log.info("URL is in whitelist [{}]", url);
            return;
        }

        // 3. 解析关联的IP地址
        InetAddress[] addresses;
        try {
            addresses = InetAddress.getAllByName(host);
        } catch (UnknownHostException e) {
            // 如果无法解析域名，放通处理
            log.warn("can not get host [{}], url check interrupt", url);
            return;
        }
        for (InetAddress addr : addresses) {
            String ip = addr.getHostAddress();

            // 4. 检查IP是否在黑名单
            if (toolUrlBlackList.contains(ip)) {
                log.error("IP is blocked by blacklist [{}]", ip);
                throw new AgentStudioException(StudioError.URL_BLOCKED_BLOCK_LIST);
            }

            // 5. 检查是否为内网IP
            if (isInternalIp(addr, projectId)) {
                log.error("Access to internal network is forbidden [{}]", ip);
                throw new AgentStudioException(StudioError.ACCESS_INTER_NETWORK_FORBIDDEN);
            }
        }
    }

    /**
     * 判断 url 是否整串就是一个占位符（运行期才解析，应跳过 URI/IP/SSRF 校验）。
     * 支持三种形态：``{}``（空占位）、``${_env.plugin_url_params.VAR}``（后端存储格式）。
     * 注意：用户输入形态的 ``{VAR}`` 在入库前已被前端 convertModelApiUrlToBackendFormat 转成
     * ``${_env.plugin_url_params.VAR}``，后端不需要单独识别 ``{VAR}``。
     */
    private boolean isFullPlaceholder(String url) {
        if (USER_EMPTY_PLACEHOLDER.equals(url)) {
            return true;
        }
        return VALID_ENV_PLACEHOLDER_FULL.matcher(url).matches();
    }

    /**
     * 校验 apiUrl 中的环境变量占位符语法。
     *
     * <p>与前端创建模型严格对齐：占位符只能是<strong>整串</strong>的 {@code ${_env.plugin_url_params.VAR}}
     * 或 {@code {}}，URL 中间不得嵌占位符（{@code https://${VAR}/v} 这类"半占位符"写法在创建页就被
     * {@code USER_URL_PATTERN = /^https?:\/\/[^{}\s]+$/i} 拒绝）。
     *
     * <p>校验规则：
     * <ol>
     *   <li>整串为 {@code {}}（用户空占位）→ 放行；</li>
     *   <li>整串为 {@code ${_env.plugin_url_params.VAR}}（VAR 命名符合环境变量命名正则）→ 放行；</li>
     *   <li>整串为 {@code ${...}} 但形态非法（如 {@code ${evil.var}}、VAR 命名非法）→ 拒绝；</li>
     *   <li>非整串占位符但 URL 中含 {@code {/}} 字符（内联占位符或未闭合花括号）→ 拒绝。</li>
     * </ol>
     * 错误抛 {@link StudioError#MODEL_ENV_VAR_UNRESOLVED}，与 Python 运行期
     * {@code MD_ENV_VAR_UNRESOLVED} 语义对齐。
     */
    public void validateEnvVarPlaceholders(String url) {
        if (StringUtils.isEmpty(url)) {
            return;
        }
        String trimmed = url.trim();
        // 整串合法占位符（后端格式 ${_env.plugin_url_params.VAR} 或空占位 {}）→ 放行
        if (isFullPlaceholder(trimmed)) {
            return;
        }
        // 整串 ${...} 但形态非法（不是 ${_env.plugin_url_params.VAR}）→ 拒绝
        if (trimmed.startsWith("${") && trimmed.endsWith("}")) {
            log.error("Invalid full-string env var placeholder (not ${_env.plugin_url_params.VAR}): [{}]", url);
            throw new AgentStudioException(StudioError.MODEL_ENV_VAR_UNRESOLVED);
        }
        // 整串 {...}（用户形态 {VAR}）：前端提交前已转换为后端格式，入库/导入文件均不应出现此形态 → 拒绝
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            log.error("User-format placeholder {VAR} must be converted to backend format before save: [{}]", url);
            throw new AgentStudioException(StudioError.MODEL_ENV_VAR_UNRESOLVED);
        }
        // 其他情况（URL 中间嵌 ${...}、未闭合花括号、裸 {/}）一律拒绝——创建页不允许，导入侧对齐。
        if (trimmed.indexOf('{') >= 0 || trimmed.indexOf('}') >= 0) {
            log.error("URL must not contain inline placeholder/braces (only whole-string placeholder allowed): [{}]", url);
            throw new AgentStudioException(StudioError.MODEL_ENV_VAR_UNRESOLVED);
        }
    }

    /**
     * 判断 apiUrl 是否含环境变量占位符 ``${_env.plugin_url_params.VAR}``。
     *
     * <p>含占位符的模型，其真实 URL 由 Python 运行期 ``env_resolver.py`` 按环境变量解析，
     * 在发布/鉴权/创建/更新等可用性探测时无法预知目标环境运行时变量，探测字面占位符必失败。
     * 故探测入口据此跳过占位符模型（与 Python ``resolver._build_detail`` 的 fail-fast 语义互补：
     * 运行期解析缺变量抛 MD_ENV_VAR_UNRESOLVED；导入侧探测期直接跳过）。
     *
     * <p>注意：本方法是子串匹配（任意位置含占位符都返回 true），作为探测期的安全兜底；但新写入路径
     * （创建/更新/导入）通过 {@link #validateUrlSyntax} + {@link #validateEnvVarPlaceholders}
     * 严格限制占位符只能作为 apiUrl 整串出现，内联占位符无法入库——此处的子串匹配仅用于
     * 防御历史脏数据。
     *
     * @param url 待判断的 apiUrl
     * @return 含占位符返回 true
     */
    public boolean hasEnvPlaceholder(String url) {
        if (StringUtils.isEmpty(url) || !url.contains("${")) {
            return false;
        }
        return VALID_ENV_PLACEHOLDER.matcher(url).find();
    }

    /**
     * 检查给定的URL是否在白名单中
     *
     * @param url 需要检查的URL
     * @throws AgentStudioException 如果URL不在白名单中，或者URL格式错误，或者无法解析主机名
     */
    public void checkUrlInWhiteList(String url) {
        log.info("Starting URL check for: {}", url);

        if (!enableUrlCheck || StringUtils.isEmpty(url)) {
            log.info("URL check is disabled or URL is empty");
            return;
        }

        try {
            URI parsedUri = new URI(url);
            String host = parsedUri.getHost();

            // 判断白名单中是否存在该URL
            if (toolUrlWhiteList.contains(host)) {
                log.info("URL is in whitelist: {}", url);
                return;
            }

            // 解析URL关联的IP地址，判断IP地址是否在白名单中
            InetAddress[] addresses = InetAddress.getAllByName(host);
            for (InetAddress addr : addresses) {
                String ip = addr.getHostAddress();
                if (toolUrlWhiteList.contains(ip)) {
                    log.info("IP is in whitelist: {}", url);
                    return;
                }
            }
            throw new AgentStudioException(StudioError.URL_WHITELIST_CHECK_ERROR);
        } catch (URISyntaxException e) {
            log.error("Invalid URL: {}", url, e);
            throw new AgentStudioException(StudioError.INVALID_URL);
        } catch (UnknownHostException e) {
            log.warn("can not get host [{}], url check interrupt", url);
            throw new AgentStudioException(StudioError.URL_WHITELIST_CHECK_ERROR);
        }
    }


    /**
     * 判断IP是否为内网地址
     */
    public boolean isInternalIp(InetAddress addr, String projectId) {
        // 本地回环地址
        if (addr.isAnyLocalAddress() || addr.isLoopbackAddress()) {
            return true;
        }
        // 内网地址
        return addr.isLinkLocalAddress() || addr.isSiteLocalAddress();
    }
}

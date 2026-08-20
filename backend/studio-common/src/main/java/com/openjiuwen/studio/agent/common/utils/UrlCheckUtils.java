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
     * 合法的环境变量占位符：``${_env.plugin_url_params.VAR}``。
     * 与 Python ``env_resolver.py`` / ``logging_context.py:47`` 同源，跨环境迁移模型 apiUrl 占位符以此为准。
     */
    private static final Pattern VALID_ENV_PLACEHOLDER =
        Pattern.compile("\\$\\{_env\\.plugin_url_params\\.([^}]+)\\}");

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

    public void checkUrl(String projectId, String url) {
        log.info("start to checkUrl {}", url);
        // 未开启检查（默认开启），返回
        if (!enableUrlCheck || StringUtils.isEmpty(url)) {
            log.info("not check url");
            return;
        }
        if (url.contains("{")) {
            // 含有占位符，放通处理
            return;
        }

        URI parsedUri;
        try {
            parsedUri = new URI(url);
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
     * 校验 apiUrl 中的环境变量占位符语法。
     *
     * <p>跨环境迁移的模型 apiUrl 可能含 ``${_env.plugin_url_params.VAR}`` 占位符（运行期由 Python
     * ``env_resolver.py`` 解析）。导入侧无法预知目标环境运行时变量是否存在，故此处只校验占位符
     * <b>语法</b>：所有 ``${...}`` 必须匹配 ``${_env.plugin_url_params.VAR}`` 形态；
     * 形如 ``${evil.var}`` 的非环境占位符视为语法非法，抛 {@link StudioError#MODEL_ENV_VAR_UNRESOLVED}，
     * 与 Python 运行期 ``MD_ENV_VAR_UNRESOLVED`` 语义对齐。
     *
     * <p>注意：``checkUrl`` 对含 ``{`` 的 URL 直接放通（不校验内网/黑白名单），故占位符语法校验
     * 由本方法独立承担。无 ``${`` 的 URL 直接放行。
     *
     * @param url 待校验的 apiUrl
     */
    public void validateEnvVarPlaceholders(String url) {
        if (StringUtils.isEmpty(url) || !url.contains("${")) {
            return;
        }
        Matcher matcher = PLACEHOLDER_PATTERN.matcher(url);
        while (matcher.find()) {
            String placeholder = matcher.group(0);
            if (!VALID_ENV_PLACEHOLDER.matcher(placeholder).matches()) {
                log.error("Invalid env var placeholder in url [{}]: {}", url, placeholder);
                throw new AgentStudioException(StudioError.MODEL_ENV_VAR_UNRESOLVED);
            }
        }
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

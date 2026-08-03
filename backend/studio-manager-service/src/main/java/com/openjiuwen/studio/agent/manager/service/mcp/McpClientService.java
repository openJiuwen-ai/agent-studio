/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.enums.EnumOrgType;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientSseClientTransport;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.spec.McpSchema;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.CollectionUtils;

import java.net.Authenticator;
import java.net.InetSocketAddress;
import java.net.MalformedURLException;
import java.net.PasswordAuthentication;
import java.net.ProxySelector;
import java.net.URL;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/**
 * MCP 工具调用类 - 适配 SDK 0.16.0
 * 已移除 CustomHttpClientSseClientTransport，改用官方实现 + 配置注入
 */
@Slf4j
@Component
public class McpClientService {
    private final AntPathMatcher antPathMatcher = new AntPathMatcher();

    @Value("${model.request.proxy.open:}")
    private boolean proxyOpen;

    @Value("${model.request.proxy.user:}")
    private String proxyUser;

    @Value("${model.request.proxy.password:}")
    private String proxyPassword;

    @Value("${model.request.proxy.port:8080}")
    private int proxyPort;

    @Value("${model.request.proxy.host:}")
    private String proxyHost;

    @Value("#{'${model.request.proxy.no-host:127.0.0.1}'.split(',')}")
    private Set<String> blackProxyHost;

    @jakarta.annotation.PostConstruct
    public void decryptSensitiveFields() {
        proxyPassword = CryptoUtils.decrypt(proxyPassword);
    }

    public List<McpSchema.Tool> getMcpServiceToolList(String mcpServiceName, String baseUrl, String orgType,
        Map<String, String> headers) {
        // 使用自定义配置创建同步客户端
        try (McpSyncClient client = buildMcpClient(mcpServiceName, baseUrl, orgType, headers)) {
            log.info("begin to query mcp {}'s tool list.", mcpServiceName);
            // 初始化连接
            client.initialize();
            try {
                // 设置接收的日志最低级别
                client.setLoggingLevel(McpSchema.LoggingLevel.INFO);
            } catch (Exception e) {
                log.error("Failed to set the log level.");
            }

            McpSchema.ListToolsResult tools = client.listTools();
            return tools.tools();
        } catch (Exception e) {
            log.error("query mcp {}'s tool list error. error is ", mcpServiceName, e);
            throw new AgentStudioException(StudioError.MCP_SERVICE_BUSY, e, mcpServiceName);
        }
    }

    public McpSchema.CallToolResult callMcpServiceTool(String mcpServiceName, String toolName, String baseUrl,
        Map<String, Object> params, String orgType, Map<String, String> headers) {
        // 使用自定义配置创建同步客户端
        try (McpSyncClient client = buildMcpClient(mcpServiceName, baseUrl, orgType, headers)) {
            log.info("begin to call mcp {}'s tool {}.", mcpServiceName, toolName);
            // 初始化连接
            client.initialize();
            // 设置接收的日志最低级别
            try {
                // 设置接收的日志最低级别
                client.setLoggingLevel(McpSchema.LoggingLevel.INFO);
            } catch (Exception e) {
                log.error("Failed to set the log level.");
            }

            return client.callTool(new McpSchema.CallToolRequest(toolName, params));
        } catch (Exception e) {
            log.error("call mcp {}'s tool {} error.error is ", mcpServiceName, toolName, e);
            throw new AgentStudioException(StudioError.INVOKING_MCP_SERVICE_TOOL_ERROR, e, mcpServiceName, toolName);
        }
    }

    /**
     * 构建 MCP 客户端（主入口）
     */
    @SneakyThrows
    public McpSyncClient buildMcpClient(String mcpServiceName, String baseUrl, String orgType, Map<String, String> header) {
        System.setProperty("jdk.internal.httpclient.disableHostnameVerification", "true");

        // 1. URL 健壮性处理
        if (StringUtils.isBlank(baseUrl)) {
            log.error("Base URL is null or empty for service: {}. Client build skipped.", mcpServiceName);
            return null; // 这里必须 return，否则后面还会报空指针
        }

        // 2. URL 规范化处理 (此时 baseUrl 一定不为空，放心使用)
        baseUrl = baseUrl.trim();

        if (baseUrl.endsWith("/")) {
            log.info("Trimming trailing slash from base URL.");
            baseUrl = baseUrl.substring(0, baseUrl.length() - 1);
        }

        // 删除了这里无条件调用 parsingUrl2 的逻辑
        // 之前这里会强制打印 "SSE endpoint" 日志，导致 Streamable 模式下产生误解
        // 现在改为只打印通用的入口日志
        log.info("Start building MCP Client. Service: [{}], Type: [{}], BaseURL: [{}]", mcpServiceName, orgType, baseUrl);

        // 构建 HTTP 请求头（优化逻辑）
        HttpRequest.Builder requestBuilder = HttpRequest.newBuilder();
        // 设置默认 Content-Type (如果 header 里没传，通常都要这个)
        // Header 处理优化（核心修改点）
        // 使用不区分大小写的 Map 包装用户的 header
        Map<String, String> safeHeaders = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
        if (!CollectionUtils.isEmpty(header)) {
            // 过滤 null 值，防止报错
            header.forEach((k, v) -> {
                if (k != null && v != null) {
                    safeHeaders.put(k, v);
                }
            });
        }

        // 调测出站前剥 cust- 前缀（与 LakeSearch  agent-runtime inject_customer_headers_to_mcp 同构）
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(safeHeaders, mcpServiceName);

        // A. 添加所有用户自定义 Header (使用 forEach 替代 for loop)
        if (!safeHeaders.isEmpty()) {
            log.info("Adding custom headers to request.");
            safeHeaders.forEach(requestBuilder::header);
        }

        // 1. Streamable HTTP 分支
        // 原始值是小写，这里忽略大小写进行比较（前端用的全大写）
        if (EnumOrgType.STREAMABLE_HTTP.getValue().equalsIgnoreCase(orgType)) {
            // Streamable 直接使用 baseUrl，不需要拆分 endpoint 和 sse path
            return buildStreamableHttpClient(mcpServiceName, baseUrl, requestBuilder);
        }
        // 2. SSE 分支 (默认为 SSE)
        // parsingUrl2 的调用和 SSE 特有的日志都在这个方法内部进行，避免污染 Streamable 的日志
        return buildSseClient(mcpServiceName, baseUrl, requestBuilder);
    }

    /**
     * 构建 Streamable HTTP 客户端
     */
    @SneakyThrows
    private McpSyncClient buildStreamableHttpClient(String mcpServiceName, String fullUrl, HttpRequest.Builder requestBuilder) {
        log.info("Building Streamable HTTP client for MCP {} with full url: {}", mcpServiceName, fullUrl);

        String finalBaseUrl;
        String customEndpoint = null; // 默认为 null，表示不覆盖 SDK 的默认值 "/mcp"

        try {
            URL url = new URL(fullUrl);

            // 1. 提取 BaseURL (Scheme + Host + Port)
            StringBuilder baseBuilder = new StringBuilder();
            baseBuilder.append(url.getProtocol()).append("://").append(url.getHost());
            if (url.getPort() != -1) {
                baseBuilder.append(":").append(url.getPort());
            }
            finalBaseUrl = baseBuilder.toString();

            // 2. 提取 Path (Endpoint)
            // 只有当用户显式指定了非根路径时，才提取出来
            // 比如: http://ip:port/custom -> path="/custom" -> 覆盖
            // 比如: http://ip:port -> path="" -> 不覆盖，使用SDK默认的/mcp
            String path = url.getPath();
            // 健壮性逻辑：
            // A. 不为空
            // B. 不仅仅是 "/" (如果是跟路径，就视为没填，用SDK默认的)
            if (StringUtils.isNotBlank(path) && !"/".equals(path)) {
                // C. 去除末尾的斜杠 (比如 /mcp/ -> /mcp)
                // 防止 SDK 拼接时变成 //
                if (path.endsWith("/")) {
                    path = path.substring(0, path.length() - 1);
                }

                customEndpoint = path;
            }
            log.info("Parsed Streamable config -> Base: [{}], CustomEndpoint: [{}]", finalBaseUrl, customEndpoint);

        } catch (MalformedURLException e) {
            log.warn("Failed to parse URL: {}, fallback to original full url.", fullUrl);
            // 解析失败，只能把全路径当 base 传进去
            finalBaseUrl = fullUrl;
        }

        // 3. 构建 Builder
        var transportBuilder = HttpClientStreamableHttpTransport.builder(finalBaseUrl)
            .clientBuilder(createCustHttpClient(finalBaseUrl))
            .connectTimeout(Duration.ofSeconds(120))
            .requestBuilder(requestBuilder);

        // 4. 只有存在自定义路径时，才覆盖 SDK 默认的 "/mcp"
        if (customEndpoint != null) {
            transportBuilder.endpoint(customEndpoint);
        }

        return McpClient.sync(transportBuilder.build())
            .requestTimeout(Duration.ofSeconds(120))
            .initializationTimeout(Duration.ofSeconds(120))
            .capabilities(McpSchema.ClientCapabilities.builder().roots(true).build())
            .loggingConsumer(notification ->
                log.info("Received MCP {} log message: {}", mcpServiceName, notification.data()))
            .build();
    }

    /**
     * 构建 SSE 客户端
     * 替代了之前的 CustomHttpClientSseClientTransport
     */
    @SneakyThrows
    private McpSyncClient buildSseClient(String mcpServiceName, String baseUrl, HttpRequest.Builder requestBuilder) {
        String endpoint = baseUrl;
        String sse = "/sse";

        // 仅在 SSE 模式下才调用 URL 解析逻辑
        List<String> urls = parsingUrl2(baseUrl);
        if (!urls.isEmpty()) {
            endpoint = urls.get(0);
            sse = urls.get(1);
        }

        log.info("Building SSE client for MCP {} with endpoint: {}, sse_path: {}", mcpServiceName, endpoint, sse);

        // 1. 官方 SDK 0.16.0 允许注入 clientBuilder，从而实现超时控制和代理配置。
        var transport = HttpClientSseClientTransport.builder(endpoint)
            .sseEndpoint(sse)
            .clientBuilder(createCustHttpClient(endpoint)) // 注入自定义超时配置 (30s)
            .requestBuilder(requestBuilder)
            .connectTimeout(Duration.ofSeconds(120))
            .build();

        return McpClient.sync(transport)
            .requestTimeout(Duration.ofSeconds(120))
            .initializationTimeout(Duration.ofSeconds(120))
            .capabilities(McpSchema.ClientCapabilities.builder().roots(true).build())
            .loggingConsumer(notification ->
                log.info("Received MCP {} log message: {}", mcpServiceName, notification.data()))
            .build();
    }

    /**
     * 创建自定义 HttpClient Builder
     * 这里实现了之前 Custom 类中想要的超时控制和代理功能
     */
    private HttpClient.Builder createCustHttpClient(String url)
        throws NoSuchAlgorithmException, KeyManagementException {
        TrustManager[] trustAllCerts = new TrustManager[] {
            new X509TrustManager() {
                public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                    return null;
                }
                public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
                public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) {}
            }
        };

        SSLContext sslContext = SSLContext.getInstance("TLSv1.2");
        sslContext.init(null, trustAllCerts, SecureRandom.getInstanceStrong());
        return getBuilder(sslContext, url);
    }

    public HttpClient.Builder getBuilder(SSLContext sslContext, String url) {
        // 这里设置了 connectTimeout 为 30秒
        // 之前的 Custom 类写死是 300ms，或者构造函数传入
        // 现在在这里统一管理
        log.info("Building HTTP client with SSL context and URL: {}", url);

        HttpClient.Builder clientBuilder = HttpClient.newBuilder()
            .sslContext(sslContext)
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(120));

        log.info("Proxy is not enabled. Returning base client builder.");
        if (!proxyOpen) {
            return clientBuilder;
        }

        log.info("Extracting host from URL to determine proxy behavior.");
        String urlName = getHostFromUrl(url);

        for (String pattern : blackProxyHost) {
            if (antPathMatcher.match(pattern, urlName)) {
                log.info("URL host {} matches black proxy pattern {}. Proxy will not be used.", urlName, pattern);
                return clientBuilder;
            }
        }

        log.info("No black proxy match found. Applying proxy configuration.");
        return proxyExtracted(clientBuilder);
    }
    private HttpClient.Builder proxyExtracted(HttpClient.Builder clientBuilder) {
        clientBuilder.proxy(ProxySelector.of(new InetSocketAddress(proxyHost, proxyPort)));
        if (!StringUtils.isAnyBlank(proxyUser, proxyPassword)) {
            Authenticator.setDefault(new Authenticator() {
                @Override
                protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(proxyUser, proxyPassword.toCharArray());
                }
            });
        }

        return clientBuilder;
    }

    private String getHostFromUrl(String urlString) {
        try {
            return new URL(urlString).getHost();
        } catch (MalformedURLException e) {
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_REQUEST_INTERNAL_ERROR, urlString);
        }
    }

    private static List<String> parsingUrl2(String urlStr) {
        // 这里的日志现在只会在 SSE 模式下出现
        log.info("Parsing URL for SSE: {}", urlStr);

        try {
            URL url = new URL(urlStr);
            String endpoint = url.getProtocol() + "://" + url.getHost();

            if (url.getPort() != -1) {
                endpoint += ":" + url.getPort();
            }

            // 获取路径部分
            String sse = StringUtils.substring(urlStr, endpoint.length());

            // 保留修复后的逻辑：只在路径为空时才赋予默认值，不再强制拼接 /sse
            if (StringUtils.isBlank(sse)) {
                sse = "/sse";
            }

            log.info("Parsed SSE details -> endpoint: {}, sse path: {}", endpoint, sse);
            return List.of(endpoint, sse);
        } catch (MalformedURLException e) {
            log.info("parseing url error {}", e.getMessage());
        }

        log.warn("Returning empty list due to parsing failure.");
        return List.of();
    }

}

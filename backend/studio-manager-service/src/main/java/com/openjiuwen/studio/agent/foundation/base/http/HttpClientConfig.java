/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.base.http;

import lombok.Data;

import org.apache.hc.client5.http.auth.AuthScope;
import org.apache.hc.client5.http.auth.UsernamePasswordCredentials;
import org.apache.hc.client5.http.classic.HttpClient;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.DefaultHttpRequestRetryStrategy;
import org.apache.hc.client5.http.impl.auth.BasicCredentialsProvider;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClientBuilder;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManager;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.impl.routing.DefaultProxyRoutePlanner;
import org.apache.hc.client5.http.routing.HttpRoutePlanner;
import org.apache.hc.client5.http.ssl.DefaultClientTlsStrategy;
import org.apache.hc.client5.http.ssl.HostnameVerificationPolicy;
import org.apache.hc.client5.http.ssl.NoopHostnameVerifier;
import org.apache.hc.core5.http.HttpHost;
import org.apache.hc.core5.util.TimeValue;
import org.apache.hc.core5.util.Timeout;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.StringHttpMessageConverter;
import org.springframework.stereotype.Component;
import org.springframework.web.client.DefaultResponseErrorHandler;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.DefaultUriBuilderFactory;

import java.io.IOException;
import java.nio.charset.Charset;
import java.util.List;
import java.util.Locale;

import javax.net.ssl.SSLContext;

/**
 * 请求忽略证书或校验工具类
 */
@Configuration
@ConditionalOnClass(value = {RestTemplate.class, CloseableHttpClient.class})
@Data
@Component
public class HttpClientConfig {
    private static final Logger logger = LoggerFactory.getLogger(SslContextBuilder.class);

    @Value("${knowledge.ssl.enabled}")
    private boolean sslEnabled;

    @Autowired
    private HttpClientPoolConfig httpClientPoolConfig;

    /**
     * 用于访问云服务的restTemplate
     *
     * @return RestTemplate
     */
    @Bean(name = "restTemplateForCloudService")
    public RestTemplate restTemplateForCloudService() {
        // 连接数：maxTotalConnection 和 maxConnectionPerRoute 必须要配
        checkHttpClientPoolConfig();
        HttpClientBuilder clientBuilder = createHttpClientBuilder();
        CloseableHttpClient httpClient = clientBuilder.build();
        // 创建 RestTemplate
        HttpComponentsClientHttpRequestFactory factory = new HttpComponentsClientHttpRequestFactory(httpClient);
        return createRestTemplate(factory);
    }

    /**
     * 根据代理配置构建带代理的 RestTemplate
     */
    @Bean(name = "restTemplateForCloudServiceWithProxy")
    public RestTemplate restTemplateForCloudServiceWithProxy(UserProxyConfig userProxyConfig) {
        // 检查maxTotalConnection和maxConnectionPerRoute
        checkHttpClientPoolConfig();
        // 超时配置
        HttpClientBuilder clientBuilder = createHttpClientBuilder();
        if (userProxyConfig.isEnabled()) {
            // 代理配置
            HttpHost proxy = new HttpHost(userProxyConfig.getHost(), userProxyConfig.getPort());
            HttpRoutePlanner routePlanner = new DefaultProxyRoutePlanner(proxy);
            // 代理认证（如有）
            BasicCredentialsProvider credentialsProvider = null;
            if (userProxyConfig.getUsername() != null && userProxyConfig.getPassword() != null) {
                credentialsProvider = new BasicCredentialsProvider();
                credentialsProvider.setCredentials(new AuthScope(userProxyConfig.getHost(), userProxyConfig.getPort()),
                    new UsernamePasswordCredentials(userProxyConfig.getUsername(),
                        userProxyConfig.getPassword().toCharArray()));
            }
            clientBuilder.setRoutePlanner(routePlanner);
            if (credentialsProvider != null) {
                clientBuilder.setDefaultCredentialsProvider(credentialsProvider);
            }
        }
        CloseableHttpClient httpClient = clientBuilder.build();
        // 创建 RestTemplate
        HttpComponentsClientHttpRequestFactory factory = new HttpComponentsClientHttpRequestFactory(httpClient);
        return createRestTemplate(factory);
    }

    /**
     * 创建一个clientBuilder，设置超时配置、连接池等
     *
     * @return HttpClientBuilder HttpClient 构建器
     */
    public HttpClientBuilder createHttpClientBuilder() {
        RequestConfig requestConfig = RequestConfig.custom()
            .setConnectionRequestTimeout(Timeout.ofMilliseconds(httpClientPoolConfig.getConnectionRequestTimout()))
            .setResponseTimeout(Timeout.ofSeconds(10))
            .build();
        // 构建并返回一个配置好的基于连接池的 HTTP 客户端连接管理器
        PoolingHttpClientConnectionManager poolingHttpClientConnectionManager
            = buildPoolingHttpClientConnectionManager();
        // 构建 HttpClient
        return HttpClients.custom()
            .setConnectionManager(poolingHttpClientConnectionManager)
            .setDefaultRequestConfig(requestConfig)
            .setRetryStrategy(
                new DefaultHttpRequestRetryStrategy(httpClientPoolConfig.getRetryTimes(), TimeValue.ofSeconds(1L)));
    }

    /**
     * 用于访问云服务接口的http客户端
     *
     * @return HttpClient
     */
    public HttpClient httpClientForCloudService() {
        HttpClientBuilder httpClientBuilder = HttpClientBuilder.create();
        CloseableHttpClient httpClient = null;
        try {
            PoolingHttpClientConnectionManager poolingHttpClientConnectionManager
                = buildPoolingHttpClientConnectionManager();
            // 配置连接池
            httpClientBuilder.setConnectionManager(poolingHttpClientConnectionManager).setConnectionManagerShared(true);
            // 重试次数，重试次数为可配置，重试时间间隔1s
            httpClientBuilder.setRetryStrategy(
                new DefaultHttpRequestRetryStrategy(httpClientPoolConfig.getRetryTimes(), TimeValue.ofSeconds(1L)));
            httpClientBuilder.disableRedirectHandling();
            httpClient = httpClientBuilder.build();
        } finally {
            if (httpClient != null) {
                try {
                    httpClient.close();
                } catch (IOException e) {
                    logger.error(String.format(Locale.ENGLISH, "CloseableHttpClient close failed{%s}", e.getMessage()));
                }
            }
        }
        return httpClient;
    }

    /**
     * 创建RestTemplate实例
     *
     * @param factory
     * @return
     */
    private RestTemplate createRestTemplate(ClientHttpRequestFactory factory) {
        RestTemplate restTemplate = new RestTemplate(factory);
        // 重新设置StringHttpMessageConverter字符集，解决中文乱码问题
        modifyDefaultCharset(restTemplate);
        // 设置错误处理器
        restTemplate.setErrorHandler(new DefaultResponseErrorHandler());
        // 设置restTemplate不自动对uri进行编码，由使用restTemplate发送请求时手动编码，只在发送请求时对pathVariable进行编码
        // 因为某些请求中会携带&符号，如果在restTemplate再进行编码，会导致在restTemplate中解析requestParam参数出现问题
        DefaultUriBuilderFactory uriBuilderFactory = (DefaultUriBuilderFactory) restTemplate.getUriTemplateHandler();
        uriBuilderFactory.setEncodingMode(DefaultUriBuilderFactory.EncodingMode.VALUES_ONLY);
        return restTemplate;
    }

    /**
     * 修改默认的字符集类型为utf-8
     *
     * @param restTemplate
     */
    private void modifyDefaultCharset(RestTemplate restTemplate) {
        List<HttpMessageConverter<?>> converterList = restTemplate.getMessageConverters();
        HttpMessageConverter<?> converterTarget = null;
        for (HttpMessageConverter<?> item : converterList) {
            if (StringHttpMessageConverter.class == item.getClass()) {
                converterTarget = item;
                break;
            }
        }
        if (converterTarget != null) {
            converterList.remove(converterTarget);
        }
        Charset defaultCharset = Charset.forName(httpClientPoolConfig.getCharset());
        converterList.add(1, new StringHttpMessageConverter(defaultCharset));
    }

    private void checkHttpClientPoolConfig() {
        // 连接数：maxTotalConnection 和 maxConnectionPerRoute 必须要配
        if (httpClientPoolConfig.getMaxTotalConnect() <= 0) {
            throw new IllegalArgumentException(
                "invalid maxTotalConnection: " + httpClientPoolConfig.getMaxTotalConnect());
        }
        if (httpClientPoolConfig.getMaxConnectPerRoute() <= 0) {
            throw new IllegalArgumentException(
                "invalid maxConnectionPerRoute: " + httpClientPoolConfig.getMaxConnectPerRoute());
        }
    }

    private PoolingHttpClientConnectionManager buildPoolingHttpClientConnectionManager() {
        // 校验服务端的证书
        SSLContext sslContext = SslContextBuilder.buildCommonSslContext(sslEnabled);
        DefaultClientTlsStrategy sslConnectionSocketFactory;
        if (sslEnabled) {
            // SSL开启：使用BOTH策略，在TLS握手阶段设置endpointIdentificationAlgorithm进行SAN校验，
            // 同时使用默认HostnameVerifier进行主机名验证，保障证书链校验+主机名校验的完整安全性
            sslConnectionSocketFactory = new DefaultClientTlsStrategy(sslContext,
                HostnameVerificationPolicy.BOTH, null);
        } else {
            // SSL关闭：使用CLIENT策略，不在TLS握手阶段设置endpointIdentificationAlgorithm，
            // 配合NoopHostnameVerifier跳过主机名校验，信任所有证书，用于内部服务证书不完善的场景
            sslConnectionSocketFactory = new DefaultClientTlsStrategy(sslContext,
                HostnameVerificationPolicy.CLIENT, NoopHostnameVerifier.INSTANCE);
        }
        // 创建httpClient连接池
        PoolingHttpClientConnectionManagerBuilder connectionManagerBuilder
            = PoolingHttpClientConnectionManagerBuilder.create();
        // 设置SSL连接
        connectionManagerBuilder.setTlsSocketStrategy(sslConnectionSocketFactory);
        // 最大连接数
        connectionManagerBuilder.setMaxConnTotal(httpClientPoolConfig.getMaxTotalConnect());
        // 同路由并发数
        connectionManagerBuilder.setMaxConnPerRoute(httpClientPoolConfig.getMaxConnectPerRoute());
        // 设置超时时间
        ConnectionConfig connectionConfig = ConnectionConfig.custom()
            .setConnectTimeout(Timeout.ofMilliseconds(httpClientPoolConfig.getConnectTimeout())) // 这里设置连接超时
            .setSocketTimeout(Timeout.ofMilliseconds(httpClientPoolConfig.getConnectTimeout()))
            .build();
        connectionManagerBuilder.setDefaultConnectionConfig(connectionConfig);

        return connectionManagerBuilder.build();
    }

}

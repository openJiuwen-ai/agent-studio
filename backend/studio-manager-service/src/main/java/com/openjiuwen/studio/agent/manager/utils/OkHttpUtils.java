/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.entity.plugin.AlarmLogUtil;
import com.openjiuwen.studio.agent.manager.entity.plugin.AsyncTaskParamHolder;
import com.openjiuwen.studio.agent.manager.entity.plugin.RequestResult;
import lombok.Getter;
import lombok.SneakyThrows;
import okhttp3.ConnectionPool;
import okhttp3.Credentials;
import okhttp3.Dispatcher;
import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;
import okhttp3.sse.EventSources;
import org.apache.commons.collections.MapUtils;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.PostConstruct;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.MalformedURLException;
import java.net.Proxy;
import java.net.Socket;
import java.net.SocketException;
import java.net.URL;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.util.Arrays;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * http请求工具类
 *
 */
@Component
public class OkHttpUtils {
    public static final MediaType MEDIA_TYPE_JSON = MediaType.parse("application/json; charset=utf-8");

    private static final Logger log = LoggerFactory.getLogger(OkHttpUtils.class);

    private final AntPathMatcher antPathMatcher = new AntPathMatcher();

    @Value("${okhttp.max-idle-connections}")
    private int maxIdleConnections;

    @Value("${task.async.pool-size:100}")
    private int taskAsyncPoolSize;

    @Value("${okhttp.keep-alive-duration}")
    private long keepAliveDuration;

    @Value("${okhttp.connect-timeout}")
    private int connectTimeOut;

    @Value("${okhttp.wait-timeout}")
    private int waitTimeOut;

    @Value("${okhttp.read-timeout}")
    private int readTimeOut;

    @Value("${okhttp.max-requests-perhost}")
    private int maxRequestsPerHost;

    @Value("${okhttp.max-requests}")
    private int maxRequests;

    @Value("${okhttp.ignore-cert}")
    private boolean ignoreCert;

    @Value("${model.request.proxy.open:false}")
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

    @Getter
    private OkHttpClient httpClient = null;

    @Getter
    private OkHttpClient asyncHttpClient = null;

    @Getter
    private OkHttpClient proxyHttpClient = null;

    @Autowired
    AlarmLogUtil alarmLogUtil;

    private static void buildHeader(Request.Builder builder, Map<String, String> headers) {
        if (headers != null && !headers.isEmpty()) {
            headers.forEach((key, value) -> {
                if (value != null) {
                    builder.addHeader(key, value);
                }
            });
        }
    }

    @PostConstruct
    private void init() {
        proxyPassword = CryptoUtils.decrypt(proxyPassword);
        Dispatcher dispatcher = new Dispatcher();
        dispatcher.setMaxRequestsPerHost(maxRequestsPerHost);
        dispatcher.setMaxRequests(maxRequests);
        if (ignoreCert) {
            httpClient = new OkHttpClient.Builder().sslSocketFactory(
                    new TcpNoDelaySSLSocketFactory(SSLSocketClient.getSSLSocketFactory()),
                    SSLSocketClient.getX509TrustManager())
                .hostnameVerifier(SSLSocketClient.getHostnameVerifier())
                .connectTimeout(connectTimeOut, TimeUnit.SECONDS)
                .writeTimeout(waitTimeOut, TimeUnit.SECONDS)
                .readTimeout(readTimeOut, TimeUnit.SECONDS)
                .followRedirects(false)
                .followSslRedirects(false)
                .connectionPool(new ConnectionPool(maxIdleConnections, keepAliveDuration, TimeUnit.MINUTES))
                .dispatcher(dispatcher)
                .build();
            asyncHttpClient = new OkHttpClient.Builder().sslSocketFactory(
                    new TcpNoDelaySSLSocketFactory(SSLSocketClient.getSSLSocketFactory()),
                    SSLSocketClient.getX509TrustManager())
                .hostnameVerifier(SSLSocketClient.getHostnameVerifier())
                .connectTimeout(connectTimeOut, TimeUnit.SECONDS)
                .writeTimeout(waitTimeOut, TimeUnit.SECONDS)
                .followRedirects(false)
                .connectionPool(new ConnectionPool(taskAsyncPoolSize, keepAliveDuration, TimeUnit.MINUTES))
                .dispatcher(dispatcher)
                .build();

            OkHttpClient.Builder builder = httpClient.newBuilder()
                .sslSocketFactory(new TcpNoDelaySSLSocketFactory(SSLSocketClient.getSSLSocketFactory()),
                    SSLSocketClient.getX509TrustManager())
                .hostnameVerifier(SSLSocketClient.getHostnameVerifier())
                .proxy(proxyOpen
                    ? new Proxy(Proxy.Type.HTTP, new InetSocketAddress(proxyHost, proxyPort))
                    : Proxy.NO_PROXY);
            if (!StringUtils.isAnyBlank(proxyUser, proxyPassword)) {
                builder.proxyAuthenticator((route, response) -> {
                    String credential = Credentials.basic(proxyUser, proxyPassword);
                    return response.request().newBuilder().header("Proxy-Authorization", credential).build();
                });
            }
            proxyHttpClient = builder.followRedirects(false).build();
        } else {
            httpClient = new OkHttpClient.Builder().connectTimeout(connectTimeOut, TimeUnit.SECONDS)
                .writeTimeout(waitTimeOut, TimeUnit.SECONDS)
                .readTimeout(readTimeOut, TimeUnit.SECONDS)
                .followRedirects(false)
                .followSslRedirects(false)
                .connectionPool(new ConnectionPool(maxIdleConnections, keepAliveDuration, TimeUnit.MINUTES))
                .dispatcher(dispatcher)
                .build();
            asyncHttpClient = new OkHttpClient.Builder().connectTimeout(connectTimeOut, TimeUnit.SECONDS)
                .writeTimeout(waitTimeOut, TimeUnit.SECONDS)
                .connectionPool(new ConnectionPool(taskAsyncPoolSize, keepAliveDuration, TimeUnit.MINUTES))
                .followRedirects(false)
                .dispatcher(dispatcher)
                .build();
            proxyHttpClient = httpClient.newBuilder()
                .connectTimeout(connectTimeOut, TimeUnit.SECONDS)
                .writeTimeout(waitTimeOut, TimeUnit.SECONDS)
                .connectionPool(new ConnectionPool(maxIdleConnections, keepAliveDuration, TimeUnit.MINUTES))
                .followRedirects(false)
                .dispatcher(dispatcher)
                .build();
        }
    }

    /**
     * 调用请求
     *
     * @param url 请求url
     * @param method 请求方法
     * @param headers 请求头
     * @param jsonBody 请求体
     * @return 返回请求结果
     */
    public RequestResult call(String url, Method method, Map<String, String> headers, Map<String, String> queryParams,
                              String jsonBody) {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(url).newBuilder();
        builderParams(urlBuilder, queryParams);

        Request.Builder builder = new Request.Builder().url(urlBuilder.build());
        buildHeader(builder, headers);

        RequestBody body = RequestBody.create(jsonBody, MEDIA_TYPE_JSON);

        Request request = switch (method) {
            case POST -> builder.post(body).build();
            case GET -> builder.get().build();
            case DELETE -> builder.delete(body).build();
        };

        RequestResult result = new RequestResult();
        try (Response response = getModelRequestHttpClient(url).newCall(request).execute()) {
            result.setSuccess(response.isSuccessful());
            result.setCode(response.code());
            result.setResponse(response.body() != null ? response.body().string() : "");
            result.setHeaders(response.headers());
        } catch (Exception e) {
            log.error("request failed.", e);
            result.setSuccess(false);
            result.setCode(-1);
            result.setExceptionMessage(StringUtils.defaultIfEmpty(e.getMessage(), "unknown"));
        }
        return result;
    }

    /**
     * 调用请求
     *
     * @param url 请求url
     * @param method 请求方法
     * @param headers 请求头
     * @param jsonBody 请求体
     * @return 返回请求结果
     */
    public RequestResult call(String url, Method method, Map<String, String> headers, String jsonBody) {
        return call(url, method, headers, null, jsonBody);
    }

    private void builderParams(HttpUrl.Builder urlBuilder, Map<String, String> queryParams) {
        if (!MapUtils.isEmpty(queryParams)) {
            queryParams.forEach((k, v) -> {
                urlBuilder.addQueryParameter(k, v);
            });
        }
    }

    public OkHttpClient getModelRequestHttpClient(String url) {
        if (!proxyOpen) {
            return httpClient;
        }
        String host = getHostFromUrl(url);
        for (String pattern : blackProxyHost) {
            if (antPathMatcher.match(pattern.trim(), host)) {
                return httpClient;
            }
        }
        return proxyHttpClient;
    }

    public String getHostFromUrl(String urlString) {
        try {
            return new URL(urlString).getHost();
        } catch (MalformedURLException e) {
            throw new AgentStudioException(StudioError.MD_URL_INVALID, urlString);
        }
    }

    /**
     * form-data
     */
    @SneakyThrows
    public RequestResult callFormData(String url, Method method, Map<String, String> headers,
        Map<String, String> queryParams, Map<String, String> formParams, Map<String, MultipartFile> fileParams) {
        HttpUrl.Builder urlBuilder = Objects.requireNonNull(HttpUrl.parse(url)).newBuilder();
        builderParams(urlBuilder, queryParams);

        Request.Builder builder = new Request.Builder().url(urlBuilder.build());
        buildHeader(builder, headers);

        MultipartBody.Builder multipartBuilder = new MultipartBody.Builder().setType(MultipartBody.FORM);

        // 添加表单字段
        if (formParams != null) {
            for (Map.Entry<String, String> entry : formParams.entrySet()) {
                multipartBuilder.addFormDataPart(entry.getKey(), entry.getValue());
            }
        }

        // 添加文件
        if (fileParams != null) {
            for (Map.Entry<String, MultipartFile> entry : fileParams.entrySet()) {
                MultipartFile multipartFile = entry.getValue();
                if (!multipartFile.isEmpty()) {
                    // 创建RequestBody
                    RequestBody fileBody = RequestBody.create(multipartFile.getBytes(), MediaType.parse("application/octet-stream"));
                    // 添加到multipartBuilder
                    multipartBuilder.addFormDataPart(entry.getKey(), multipartFile.getOriginalFilename(), fileBody);
                }
            }
        }

        Request request = builder
                .method(method.name(), multipartBuilder.build())
                .build();

        RequestResult result = new RequestResult();
        try (Response response = httpClient.newCall(request).execute()) {
            result.setSuccess(response.isSuccessful());
            result.setCode(response.code());
            result.setResponse(response.body() != null ? response.body().string() : "");
            result.setHeaders(response.headers());
        } catch (IOException e) {
            log.error("Request failed.", e);
            result.setSuccess(false);
            result.setCode(-1);
            result.setExceptionMessage(StringUtils.defaultIfEmpty(e.getMessage(), "unknown"));
        }
        return result;
    }



    /**
     * 调用删除请求
     *
     * @param url 请求url
     * @param headers 请求头
     * @param bodyJson 请求体
     * @return 返回请求结果
     */
    public RequestResult delete(String url, Map<String, String> headers, String bodyJson) {
        return call(url, Method.DELETE, headers, bodyJson);
    }

    /**
     * 流式请求
     *
     * @param url 请求url
     * @param headers 请求头
     * @param json 请求体
     * @param eventSourceListener 监听
     * @return 返回是否执行成功
     */
    public boolean stream(String url, Map<String, String> headers, String json,
        EventSourceListener eventSourceListener) {
        return stream(url, headers, json, eventSourceListener, null);
    }

    /**
     * 流式请求
     *
     * @param url 请求url
     * @param headers 请求头
     * @param json 请求体
     * @param eventSourceListener 监听
     * @return 返回是否执行成功
     */
    public boolean stream(String url, Map<String, String> headers, String json, EventSourceListener eventSourceListener,
        AsyncTaskParamHolder asyncTaskParamHolder) {
        try {
            RequestBody body = RequestBody.create(json, MEDIA_TYPE_JSON);
            Request.Builder builder = new Request.Builder();
            buildHeader(builder, headers);
            Request request = builder.url(url).post(body).build();
            EventSource.Factory factory;
            if (asyncTaskParamHolder != null && asyncTaskParamHolder.isAsync()) {
                // 新增异步接口线程池，供异步接口调用, 新增extra_time防止okhttp未超时，latch超时，异步异常未抛出
                OkHttpClient dynamicClient = asyncHttpClient.newBuilder()
                    .readTimeout(asyncTaskParamHolder.getTimeout(), TimeUnit.MILLISECONDS)
                    .build();
                factory = EventSources.createFactory(dynamicClient);
                log.error("Use async http client.");
            } else {
                factory = EventSources.createFactory(httpClient);
            }
            // 创建事件
            log.info("http stream request, url: {}", url);
            EventSource eventSource = factory.newEventSource(request, eventSourceListener);
            if (asyncTaskParamHolder != null && asyncTaskParamHolder.isAsync()) {
                log.error("Use async http client.");
                asyncTaskParamHolder.setEventSource(eventSource);
            }
            return true;
        } catch (Exception e) {
            log.error("http stream request, url: {} failed", url, e);
            alarmLogUtil.logAlarm("WORKFLOW", "http stream request, failed, url:" + url, e.getMessage());
        }
        return false;
    }

    /**
     * 方法类型枚举
     */
    public enum Method {
        POST,
        GET,
        DELETE
    }

    public class SSLSocketClient {

        // 获取这个SSLSocketFactory
        public static SSLSocketFactory getSSLSocketFactory() {
            try {
                SSLContext sslContext = SSLContext.getInstance("TLSv1.2");
                sslContext.init(null, getTrustManager(), SecureRandom.getInstanceStrong());
                return sslContext.getSocketFactory();
            } catch (Exception e) {
                throw new AgentStudioException(StudioError.HTTP_CLIENT_INIT_FAILED);
            }
        }

        // 获取TrustManager
        private static TrustManager[] getTrustManager() {
            return new TrustManager[] {
                new X509TrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {
                    }

                    @Override
                    public void checkServerTrusted(X509Certificate[] chain, String authType) {
                    }

                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[] {};
                    }
                }
            };
        }

        // 获取HostnameVerifier
        public static HostnameVerifier getHostnameVerifier() {
            return (hostname, session) -> !"".equals(hostname);
        }

        public static X509TrustManager getX509TrustManager() {
            X509TrustManager trustManager = null;
            try {
                TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance(
                    TrustManagerFactory.getDefaultAlgorithm());
                trustManagerFactory.init((KeyStore) null);
                TrustManager[] trustManagers = trustManagerFactory.getTrustManagers();
                if (trustManagers.length != 1 || !(trustManagers[0] instanceof X509TrustManager)) {
                    throw new IllegalStateException(
                        "Unexpected default trust managers:" + Arrays.toString(trustManagers));
                }
                trustManager = (X509TrustManager) trustManagers[0];
            } catch (Exception e) {
                log.error("trust manager init failed.", e);
            }

            return trustManager;
        }
    }

    public static class TcpNoDelaySSLSocketFactory extends SSLSocketFactory {
        private final SSLSocketFactory delegate;

        public TcpNoDelaySSLSocketFactory(SSLSocketFactory delegate) {
            this.delegate = delegate;
        }

        private Socket enableTcpNoDelay(Socket socket) throws SocketException {
            if (socket != null) {
                socket.setTcpNoDelay(true);
            }
            return socket;
        }

        @Override
        public Socket createSocket() throws IOException {
            return enableTcpNoDelay(delegate.createSocket());
        }

        @Override
        public Socket createSocket(String host, int port) throws IOException {
            return enableTcpNoDelay(delegate.createSocket(host, port));
        }

        @Override
        public Socket createSocket(String host, int port, InetAddress localHost, int localPort) throws IOException {
            return enableTcpNoDelay(delegate.createSocket(host, port, localHost, localPort));
        }

        @Override
        public Socket createSocket(InetAddress host, int port) throws IOException {
            return enableTcpNoDelay(delegate.createSocket(host, port));
        }

        @Override
        public Socket createSocket(InetAddress address, int port, InetAddress localAddress, int localPort)
            throws IOException {
            return enableTcpNoDelay(delegate.createSocket(address, port, localAddress, localPort));
        }

        @Override
        public Socket createSocket(Socket s, String host, int port, boolean autoClose) throws IOException {
            return enableTcpNoDelay(delegate.createSocket(s, host, port, autoClose));
        }

        @Override
        public String[] getDefaultCipherSuites() {
            return delegate.getDefaultCipherSuites();
        }

        @Override
        public String[] getSupportedCipherSuites() {
            return delegate.getSupportedCipherSuites();
        }
    }
}

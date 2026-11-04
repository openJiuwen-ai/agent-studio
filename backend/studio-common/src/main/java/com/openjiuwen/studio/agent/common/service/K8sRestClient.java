/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;

/**
 * K8s in-cluster REST 客户端(镜像瘦身第一部分 1B,2026-11-04)。
 *
 * <p>背景:原经 io.kubernetes:client-java 的 {@code CoreV1Api.listPodForAllNamespaces}
 * 读取 pod 资源;去除 client-java 依赖(约 15MB+随行链)后改为 K8s 原生 REST API
 * 直调——读侧语义与原实现一致(list pods all namespaces,取各容器
 * resources.limits.cpu)。
 *
 * <p>实现:JDK 内置 {@link HttpClient}(零新依赖)+ in-cluster ServiceAccount:
 * <ul>
 *   <li>token:{@code /var/run/secrets/kubernetes.io/serviceaccount/token}</li>
 *   <li>CA:{@code /var/run/secrets/kubernetes.io/serviceaccount/ca.crt}
 *       构建信任(原实现 setVerifyingSsl(false) 关闭校验——此处改为集群 CA
 *       真实校验,in-cluster CA 恒挂载,安全性优于原样)</li>
 *   <li>地址:{@code https://$KUBERNETES_SERVICE_HOST:$KUBERNETES_SERVICE_PORT}
 *       /api/v1/pods}(与 Config.fromCluster() 同源)</li>
 * </ul>
 */
public final class K8sRestClient {

    private static final String SERVICEACCOUNT_DIR = "/var/run/secrets/kubernetes.io/serviceaccount";
    private static final String TOKEN_FILE = SERVICEACCOUNT_DIR + "/token";
    private static final String CA_CERT_FILE = SERVICEACCOUNT_DIR + "/ca.crt";
    private static final String PODS_URL_FORMAT = "https://%s:%s/api/v1/pods";
    private static final Duration REQUEST_TIMEOUT = Duration.ofSeconds(30);
    /** 瞬时失败重试次数(评审修订 2026-11-04 LOW:原 client-java 内建重试) */
    private static final int MAX_RETRIES = 2;
    private static final long RETRY_DELAY_MS = 1000;

    private static final ObjectMapper JSON = new ObjectMapper();

    /** 惰性单例(评审修订 2026-11-04:LicenseControlSchedule 定时调用,每
     *  次 new HttpClient 会重复构建 SSL 上下文/连接池——单例复用)。
     *  首次调用初始化(需读 ServiceAccount CA);初始化失败不缓存,
     *  下次调用重试(集群凭据可能挂载晚于进程启动)。 */
    private static volatile HttpClient sharedClient;

    private K8sRestClient() {
    }

    /**
     * 全命名空间 pod 概要(名称 + 标签 + 各容器 CPU limit 串)。
     *
     * @return pod 列表(空集群返回空列表)
     * @throws IOException 集群凭据缺失、HTTP 失败或响应非 2xx
     */
    public static List<PodSummary> listPodsAllNamespaces() throws IOException {
        String host = System.getenv("KUBERNETES_SERVICE_HOST");
        String port = System.getenv("KUBERNETES_SERVICE_PORT");
        if (host == null || host.isEmpty() || port == null || port.isEmpty()) {
            throw new IOException("not running in kubernetes: KUBERNETES_SERVICE_HOST/PORT absent");
        }
        String token = Files.readString(Path.of(TOKEN_FILE), StandardCharsets.UTF_8).trim();
        HttpClient client = getOrCreateClient();
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(String.format(PODS_URL_FORMAT, host, port)))
                .header("Authorization", "Bearer " + token)
                .timeout(REQUEST_TIMEOUT)
                .GET()
                .build();
        HttpResponse<String> response = sendWithRetry(client, request);
        if (response.statusCode() / 100 != 2) {
            throw new IOException("k8s pods request failed: HTTP " + response.statusCode());
        }
        JsonNode items = JSON.readTree(response.body()).path("items");
        List<PodSummary> pods = new ArrayList<>();
        for (JsonNode item : items) {
            String name = item.path("metadata").path("name").asText(null);
            if (name == null) {
                continue;
            }
            Map<String, String> labels = readLabels(item.path("metadata").path("labels"));
            List<String> cpuLimits = new ArrayList<>();
            for (JsonNode container : item.path("spec").path("containers")) {
                String cpu = container.path("resources").path("limits").path("cpu").asText(null);
                if (cpu != null && !cpu.isEmpty()) {
                    cpuLimits.add(cpu);
                }
            }
            pods.add(new PodSummary(name, labels, cpuLimits));
        }
        return pods;
    }

    /**
     * K8s CPU 数量解析(与原 Quantity.getNumber 语义对齐)。
     *
     * @param cpuStr cpu limit 串,如 "100m"(毫核)或 "2"(整核)
     * @return CPU 核数
     */
    public static double parseCpu(String cpuStr) {
        if (cpuStr == null || cpuStr.isEmpty()) {
            return 0.0;
        }
        if (cpuStr.endsWith("m")) {
            return Double.parseDouble(cpuStr.substring(0, cpuStr.length() - 1)) / 1000.0;
        }
        return Double.parseDouble(cpuStr);
    }

    /**
     * 是否运行在 K8s pod 内(与原实现一致:ServiceAccount 环境变量存在)。
     */
    public static boolean isRunningInKubernetes() {
        String host = System.getenv("KUBERNETES_SERVICE_HOST");
        String port = System.getenv("KUBERNETES_SERVICE_PORT");
        return host != null && !host.isEmpty() && port != null && !port.isEmpty();
    }

    /**
     * 带重试的 HTTP 发送(评审修订 2026-11-04 LOW:瞬时网络抖动重试,
     * 对齐原 client-java 的内建重试;仅 IOException 重试,中断不重)。
     */
    private static HttpResponse<String> sendWithRetry(HttpClient client, HttpRequest request)
            throws IOException {
        IOException lastError = null;
        for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                return client.send(request, HttpResponse.BodyHandlers.ofString());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("k8s pods request interrupted", e);
            } catch (IOException e) {
                lastError = e;
                if (attempt < MAX_RETRIES) {
                    try {
                        Thread.sleep(RETRY_DELAY_MS * (attempt + 1));
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new IOException("k8s pods retry interrupted", ie);
                    }
                }
            }
        }
        throw new IOException("k8s pods request failed after " + (MAX_RETRIES + 1) + " attempts", lastError);
    }

    private static HttpClient getOrCreateClient() throws IOException {
        HttpClient existing = sharedClient;
        if (existing != null) {
            return existing;
        }
        synchronized (K8sRestClient.class) {
            if (sharedClient == null) {
                sharedClient = HttpClient.newBuilder()
                        .sslContext(buildSslContext())
                        .connectTimeout(REQUEST_TIMEOUT)
                        .build();
            }
            return sharedClient;
        }
    }

    private static SSLContext buildSslContext() throws IOException {
        try {
            CertificateFactory factory = CertificateFactory.getInstance("X.509");
            Certificate ca = factory.generateCertificate(
                    new java.io.ByteArrayInputStream(Files.readAllBytes(Path.of(CA_CERT_FILE))));
            KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
            keyStore.load(null, null);
            keyStore.setCertificateEntry("k8s-ca", ca);
            TrustManagerFactory tmf = TrustManagerFactory.getInstance(
                    TrustManagerFactory.getDefaultAlgorithm());
            tmf.init(keyStore);
            TrustManager[] managers = tmf.getTrustManagers();
            SSLContext context = SSLContext.getInstance("TLS");
            context.init(null, managers, null);
            return context;
        } catch (Exception e) {
            throw new IOException("fail to build in-cluster SSL context from " + CA_CERT_FILE, e);
        }
    }

    private static Map<String, String> readLabels(JsonNode labelsNode) {
        if (labelsNode == null || !labelsNode.isObject() || labelsNode.isEmpty()) {
            return Collections.emptyMap();
        }
        Map<String, String> labels = new java.util.HashMap<>();
        // ObjectNode 的 fields() 产出 Map.Entry(键值对);
        // 普通迭代器只产出值节点,取不到标签键名
        labelsNode.fields().forEachRemaining(
                entry -> labels.put(entry.getKey(), entry.getValue().asText("")));
        return labels;
    }

    /**
     * pod 概要(REST 视角的 K8sResourceRequirements 投影)。
     */
    public static final class PodSummary {
        private final String name;
        private final Map<String, String> labels;
        private final List<String> containerCpuLimits;

        /**
         * 构造 pod 概要。
         *
         * @param name pod 名称
         * @param labels pod 标签(可空,内部转为不可变)
         * @param containerCpuLimits 各容器 CPU limit 串(如 "100m"/"2")
         */
        public PodSummary(String name, Map<String, String> labels, List<String> containerCpuLimits) {
            this.name = name;
            this.labels = labels == null ? Collections.emptyMap() : Map.copyOf(labels);
            this.containerCpuLimits = containerCpuLimits == null
                    ? Collections.emptyList() : List.copyOf(containerCpuLimits);
        }

        public String getName() {
            return name;
        }

        public Map<String, String> getLabels() {
            return labels;
        }

        public List<String> getContainerCpuLimits() {
            return containerCpuLimits;
        }
    }
}

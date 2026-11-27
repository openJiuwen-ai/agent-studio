/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rdc;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.config.RdcProperties;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * RDC 注册发现客户端
 *
 * <p>FEAT-131: 封装与 RDC 的 A1（注册）/ A3（注销）交互</p>
 * <p>使用 java.net.http.HttpClient，不引入额外依赖</p>
 */
@Slf4j
@Component
public class RdcRegistrationClient {

    private final RdcProperties rdcProperties;
    private final HttpClient httpClient;

    public RdcRegistrationClient(RdcProperties rdcProperties) {
        this.rdcProperties = rdcProperties;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(rdcProperties.getTimeoutMs()))
            .build();
    }

    /**
     * A1 注册：POST {base-url}/v2/agents/{agentId}/instances
     *
     * @param agentId 应用 ID
     * @param agentCardJson Agent Card 完整 JSON 字符串
     * @return instanceId（RDC 返回的实例 ID），失败返回 null
     */
    public String register(String agentId, String agentCardJson) {
        if (!rdcProperties.isConfigured()) {
            log.warn("RDC not configured, skip registration for agent: {}", agentId);
            return null;
        }

        String url = String.format("%s/v2/agents/%s/instances", rdcProperties.getBaseUrl(), agentId);

        Map<String, Object> body = new HashMap<>();
        // RDC 要求 address 为纯主机名（不含 scheme/path）
        String runtimeHost = rdcProperties.getRuntimeBaseUrl()
            .replaceFirst("^https?://", "")
            .replaceFirst("^//", "")
            .split("/")[0]
            .split(":")[0];
        body.put("address", runtimeHost);
        body.put("port", rdcProperties.getRuntimePort());
        body.put("endpointPath", rdcProperties.getEndpointPath());
        body.put("contractVersion", "1.0.0");
        body.put("frameworkType", "JIUWEN");
        body.put("registrationMode", "STATIC");
        body.put("agentCardJson", agentCardJson);

        String bodyJson = JSON.toJSONString(body);

        try {
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("X-Tenant-ID", rdcProperties.getTenantId())
                .header("Authorization", "Bearer " + rdcProperties.getToken())
                .timeout(Duration.ofMillis(rdcProperties.getTimeoutMs()))
                .POST(HttpRequest.BodyPublishers.ofString(bodyJson))
                .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JSONObject result = JSON.parseObject(response.body());
                String instanceId = result.getString("instanceId");
                log.info("RDC A1 register success, agentId={}, instanceId={}", agentId, instanceId);
                return instanceId;
            } else {
                log.error("RDC A1 register failed, agentId={}, status={}, body={}",
                    agentId, response.statusCode(), response.body());
                return null;
            }
        } catch (Exception e) {
            log.error("RDC A1 register error, agentId={}", agentId, e);
            return null;
        }
    }

    /**
     * A3 注销：DELETE {base-url}/v2/agents/{agentId}/instances/{instanceId}
     *
     * @param agentId 应用 ID
     * @param instanceId RDC 实例 ID
     * @return true=成功（含幂等，实例已不存在也返回 true），false=失败
     */
    public boolean deregister(String agentId, String instanceId) {
        if (!rdcProperties.isConfigured()) {
            log.warn("RDC not configured, skip deregistration for agent: {}", agentId);
            return true;
        }

        if (instanceId == null || instanceId.isBlank()) {
            log.warn("RDC A3 deregister skipped, no instanceId for agent: {}", agentId);
            return true;
        }

        String url = String.format("%s/v2/agents/%s/instances/%s",
            rdcProperties.getBaseUrl(), agentId, instanceId);

        try {
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("X-Tenant-ID", rdcProperties.getTenantId())
                .header("Authorization", "Bearer " + rdcProperties.getToken())
                .timeout(Duration.ofMillis(rdcProperties.getTimeoutMs()))
                .DELETE()
                .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            // 204 = 成功，404 = 幂等（实例已不存在）
            if (response.statusCode() == 204 || response.statusCode() == 404) {
                log.info("RDC A3 deregister success, agentId={}, instanceId={}", agentId, instanceId);
                return true;
            } else {
                log.error("RDC A3 deregister failed, agentId={}, instanceId={}, status={}, body={}",
                    agentId, instanceId, response.statusCode(), response.body());
                return false;
            }
        } catch (Exception e) {
            log.error("RDC A3 deregister error, agentId={}, instanceId={}", agentId, instanceId, e);
            return false;
        }
    }
}

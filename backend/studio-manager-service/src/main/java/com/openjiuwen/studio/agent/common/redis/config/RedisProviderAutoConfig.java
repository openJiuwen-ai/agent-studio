/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.config;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisClientWrapper;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderContext;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Redis Provider 单点装配（Redisson 缺省实现，位于 studio-manager-service；
 * SPI 契约在 studio-manager-api 的 com.openjiuwen.studio.agent.common.redis）。
 *
 * 解析逻辑全部收敛到 RedisProviderResolver；本类只负责：
 * 1. 从 Spring 配置构建 RedisProviderContext（含企业专属参数透传）
 * 2. 调用解析器获取客户端（缺省 redisson / memory / custom Provider / 存量兼容）
 * 3. 包装为 RedisClientWrapper（统一日志与错误降级）
 */
@Configuration
@Lazy
public class RedisProviderAutoConfig {

    @Value("${redis.enable-log:true}")
    private boolean enableLog;

    @Autowired(required = false)
    private ObjectMapper objectMapper;

    @Bean
    public RedisClient redisClient(RedisClientConfig redisClientConfig) {
        RedisProviderContext context = buildContext(redisClientConfig);
        RedisClient client = RedisProviderResolver.resolve(redisClientConfig, context);
        return new RedisClientWrapper(client, enableLog);
    }

    // ---------------------------------------------------------------- internal

    /**
     * 从 Spring 配置构建 Provider 上下文（含企业专属参数解析与透传）。
     */
    private RedisProviderContext buildContext(RedisClientConfig config) {
        Map<String, Object> rawConfig = parseProviderConfig(config);
        List<String> clusterNodes = parseCsv(config.getClusterNodeList());
        List<String> sentinelNodes = parseCsv(config.getSentinelPorts());
        List<String> targetPorts = parseCsv(config.getTargetPorts());

        return new RedisProviderContext.Builder()
            .singleNode(config.getRedisHost(), config.getRedisPort(), 0)
            .auth(config.getRedisPassword())
            .poolSizes(config.getConnectionMinimumIdleSize(), config.getConnectionPoolSize())
            .clusterNodes(clusterNodes)
            .sentinel(config.getMasterName(), sentinelNodes, targetPorts)
            .rawConfig(rawConfig)
            .build();
    }

    /**
     * 解析 Provider 专属配置：优先内联 JSON 字符串，其次文件路径。
     * 框架不解析内部字段，只做格式校验后透传。
     */
    private Map<String, Object> parseProviderConfig(RedisClientConfig config) {
        // 1. 内联 JSON 字符串
        String inline = config.getProviderConfig();
        if (inline != null && !inline.isBlank()) {
            return parseJson(inline.trim());
        }

        // 2. 文件路径
        String filePath = config.getProviderConfigFile();
        if (filePath != null && !filePath.isBlank()) {
            try (InputStream is = new FileInputStream(new File(filePath.trim()))) {
                ObjectMapper mapper = objectMapper != null ? objectMapper : new ObjectMapper();
                Map<String, Object> result = mapper.readValue(is,
                    new TypeReference<Map<String, Object>>() { });
                return result != null ? result : Collections.emptyMap();
            } catch (Exception e) {
                throw new IllegalArgumentException(
                    "redis.provider-config-file 读取或解析失败: " + filePath, e);
            }
        }

        return Collections.emptyMap();
    }

    private Map<String, Object> parseJson(String json) {
        try {
            ObjectMapper mapper = objectMapper != null ? objectMapper : new ObjectMapper();
            Map<String, Object> result = mapper.readValue(json,
                new TypeReference<Map<String, Object>>() { });
            return result != null ? result : Collections.emptyMap();
        } catch (Exception e) {
            // 不回显 e.getMessage()：Jackson 的消息含 [Source: (String)"..."] 原文片段，
            // provider-config 可能携带企业凭证（appId/passport），不得泄入启动日志
            throw new IllegalArgumentException(
                "redis.provider-config JSON 解析失败: " + e.getClass().getSimpleName(), e);
        }
    }

    private List<String> parseCsv(String csv) {
        if (csv == null || csv.isBlank()) {
            return Collections.emptyList();
        }
        return Arrays.stream(csv.split(","))
            .map(String::trim)
            .filter(s -> !s.isEmpty())
            .toList();
    }
}

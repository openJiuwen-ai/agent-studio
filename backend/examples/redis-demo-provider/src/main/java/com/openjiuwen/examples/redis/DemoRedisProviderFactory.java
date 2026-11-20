/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.examples.redis;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderContext;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderException;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderFactory;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 演示 Provider 工厂——企业自研接入的标准样板。
 *
 * 注册方式（二选一）：
 * 1. ServiceLoader：jar 内 META-INF/services/...RedisProviderFactory 声明本类，
 *    配置 redis.client-type=custom（classpath 仅此一个工厂时自动选取）；
 * 2. 显式指定：redis.provider-class=com.openjiuwen.examples.redis.DemoRedisProviderFactory。
 *
 * 企业专属参数经 redis.provider-config（JSON）透传到 {@link RedisProviderContext#getRawConfig(String)}，
 * 框架不解析其内部字段——本示例读取 logCommands / latencyMillis 两个演示参数。
 */
public class DemoRedisProviderFactory implements RedisProviderFactory {

    private static final Logger log = LoggerFactory.getLogger(DemoRedisProviderFactory.class);

    @Override
    public RedisClient create(RedisProviderContext context) {
        try {
            boolean logCommands = context.getRawConfig("logCommands", Boolean.FALSE);
            Object latencyObj = context.getRawConfig("latencyMillis");
            long latencyMillis = latencyObj instanceof Number number ? number.longValue() : 0L;

            log.info("Demo Redis Provider 装配: logCommands={}, latencyMillis={}ms, host={}:{}",
                logCommands, latencyMillis, context.getHost(), context.getPort());

            return new DemoRedisClient(logCommands, latencyMillis);
        } catch (Exception e) {
            throw new RedisProviderException("DemoRedisProviderFactory 创建失败", e);
        }
    }
}

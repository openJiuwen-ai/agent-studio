/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.spi;

import com.openjiuwen.studio.agent.common.redis.exception.RedisAccessException;

/**
 * Redis Provider 装配失败统一异常（启动期 fail-fast，不静默降级）。
 *
 * 抛出场景：
 * - provider-class 指定的类不存在或不可加载
 * - 实现类未实现 RedisProviderFactory / RedisClient 接口
 * - 工厂 create() 抛出异常
 * - 配置缺失（如 custom 模式但未指定 provider-class）
 *
 * J4 归族：{@link RedisAccessException} 子类（operation=provider，无 key 上下文）。
 */
public class RedisProviderException extends RedisAccessException {

    public RedisProviderException(String message) {
        super(message, null, null, "provider");
    }

    public RedisProviderException(String message, Throwable cause) {
        super(message, cause, null, "provider");
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import feign.Capability;
import feign.Client;

/**
 * COM-04 响应 P1-2: Feign {@link Capability}——包装 Client，使 transport failure
 * （DNS/connect/TLS/timeout，无 HTTP 响应）保留显式下游身份（RUNTIME/BUILDER），
 * 不落入全局 {@code EXTERNAL} 兜底。
 *
 * <p>采用命名 public 类而非匿名类：Feign 框架对 {@code enrich} 的调用在部分
 * spring-cloud-openfeign 版本经反射执行，匿名（包级私有）类跨包不可访问会抛
 * {@link IllegalAccessException}；public 命名类保证可访问性。行为与 COM-03
 * 旧分支的匿名 {@code Capability} 等价。
 *
 * <p>不增加重试：{@link ServiceAwareFeignClient} 抛出的 {@link DownstreamFailureException}
 * 不是 {@code RetryableException}，Feign 不会重试。
 */
public final class ServiceAwareFeignCapability implements Capability {

    private final DownstreamService service;
    private final DownstreamErrorParser parser;

    public ServiceAwareFeignCapability(DownstreamService service, DownstreamErrorParser parser) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamService must not be null");
        }
        if (parser == null) {
            throw new IllegalArgumentException("DownstreamErrorParser must not be null");
        }
        this.service = service;
        this.parser = parser;
    }

    @Override
    public Client enrich(Client client) {
        if (client == null) {
            throw new IllegalArgumentException("Delegate Client must not be null");
        }
        return new ServiceAwareFeignClient(service, client, parser);
    }
}

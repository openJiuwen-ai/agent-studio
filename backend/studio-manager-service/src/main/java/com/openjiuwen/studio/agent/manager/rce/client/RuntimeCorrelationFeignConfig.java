/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFeignErrorDecoder;
import com.openjiuwen.studio.agent.manager.exception.downstream.ServiceAwareFeignCapability;
import com.openjiuwen.studio.agent.manager.exception.downstream.ServiceAwareFeignClient;
import feign.Capability;
import feign.Client;
import feign.codec.ErrorDecoder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;

/**
 * Runtime Feign 专用配置（COM-04 §6.1）。
 *
 * <p>仅供 {@code @FeignClient(name = "agentRuntime", configuration = ...)} 引用；
 * <b>不得</b>添加 {@code @Configuration}——否则会被组件扫描成全局 Feign 配置，
 * 把 Runtime 策略泄漏到其他客户端。注入 {@code agent_runtime_endpoint} 作为受信任 origin。
 *
 * <p>COM-03：注入 Runtime 专用 {@link ErrorDecoder}（{@code DownstreamFeignErrorDecoder}），
 * 显式标记下游身份为 {@code RUNTIME}，解析下游 body 并抛 {@code DownstreamFailureException}。
 * {@code ServiceAwareFeignClient} 包装 Client，使 transport failure 保留 RUNTIME 身份。
 */
public class RuntimeCorrelationFeignConfig implements CorrelationFeignConfig {

    @Bean
    public RuntimeCorrelationFeignInterceptor runtimeCorrelationFeignInterceptor(
        @Value("${agent_runtime_endpoint:http://127.0.0.1:31014}") String runtimeEndpoint) {
        return new RuntimeCorrelationFeignInterceptor(runtimeEndpoint);
    }

    @Bean
    public ErrorDecoder runtimeErrorDecoder() {
        return new DownstreamFeignErrorDecoder(DownstreamService.RUNTIME,
            new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog())));
    }

    @Bean
    public Capability runtimeServiceAwareCapability() {
        DownstreamErrorParser parser =
            new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
        return new ServiceAwareFeignCapability(DownstreamService.RUNTIME, parser);
    }
}

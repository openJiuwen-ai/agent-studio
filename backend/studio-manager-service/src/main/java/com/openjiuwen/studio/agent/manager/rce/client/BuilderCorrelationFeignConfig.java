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
 * Builder Feign 专用配置（COM-04 §6.1）。
 *
 * <p>仅供 {@code @FeignClient(name = "agentBuilder", configuration = ...)} 引用；
 * <b>不得</b>添加 {@code @Configuration}——防止组件扫描成全局 Feign 配置。
 * 注入 {@code agent_builder_endpoint} 作为受信任 origin。
 *
 * <p>COM-03：注入 Builder 专用 {@link ErrorDecoder}（{@code DownstreamFeignErrorDecoder}），
 * 显式标记下游身份为 {@code BUILDER}。{@code ServiceAwareFeignClient} 包装 Client，
 * 使 transport failure 保留 BUILDER 身份，不落入全局 EXTERNAL 兜底。
 */
public class BuilderCorrelationFeignConfig implements CorrelationFeignConfig {

    @Bean
    public BuilderCorrelationFeignInterceptor builderCorrelationFeignInterceptor(
        @Value("${agent_builder_endpoint:http://127.0.0.1:31015}") String agentBuilderEndpoint) {
        return new BuilderCorrelationFeignInterceptor(agentBuilderEndpoint);
    }

    @Bean
    public ErrorDecoder builderErrorDecoder() {
        return new DownstreamFeignErrorDecoder(DownstreamService.BUILDER,
            new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog())));
    }

    @Bean
    public Capability builderServiceAwareCapability() {
        DownstreamErrorParser parser =
            new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
        return new ServiceAwareFeignCapability(DownstreamService.BUILDER, parser);
    }
}

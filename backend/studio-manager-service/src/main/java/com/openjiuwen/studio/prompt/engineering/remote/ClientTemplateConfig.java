/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.remote;

import lombok.extern.slf4j.Slf4j;

import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.web.client.DefaultResponseErrorHandler;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamClientTemplateErrorHandler;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser;
import com.openjiuwen.studio.agent.manager.exception.downstream.ServiceAwareClientHttpRequestInterceptor;
import com.openjiuwen.studio.agent.manager.observability.BuilderCorrelationInterceptor;

/**
 * 功能描述 各模块定制化clientTemplate
 *
 */
@Configuration
@Slf4j
public class ClientTemplateConfig {
    /**
     * 远端服务client
     *
     * @param factory
     * @return
     */
    @Bean(name = "remoteClientTemplate")
    public ClientTemplate getManagerClient(ClientHttpRequestFactory factory) {
        return new ClientTemplate(factory, new DefaultResponseErrorHandler() {
            @Override
            protected boolean hasError(@NotNull HttpStatusCode statusCode) {
                return statusCode.is5xxServerError() || statusCode.value() == 429;
            }
        });
    }

    /**
     * Builder 专用 clientTemplate（COM-04 §6.4）。
     * 挂载 {@link BuilderCorrelationInterceptor}：固定 BUILDER 策略，
     * 注入 request/trace、删除 execution，校验 origin 与 agent_builder_endpoint 一致。
     *
     * <p><b>COM-03 RestTemplate 机制已接线（SYNC-01 P5-R2 方法级语义合并）</b>：
     * {@code DownstreamClientTemplateErrorHandler}（5xx→parser→DownstreamFailureException）
     * + {@code ServiceAwareClientHttpRequestInterceptor}（transport IOException→
     * DownstreamFailureException，BUILDER 身份）。{@code JiuWenPromptTaskJob.deleteTask/
     * getTaskDetail} 改 {@code catch(DownstreamFailureException)}，按解析的 builder code 保
     * sync_01 业务语义：102155→幂等（deleteTask 静默 / getTaskDetail JOB_NOT_FOUND_IN_BUILDER）、
     * LLM 码→CALL_LLM_EXECUTION_ERROR、其余→DELETE_OPTIMIZATION_TASK/GET_OPTIMIZATION_TASK。
     * parser 桥接读 builder 裸 int {@code "code"}（等迁 canonical8 后过时）。
     */
    @Bean(name = "builderClientTemplate")
    public ClientTemplate getBuilderClient(ClientHttpRequestFactory factory,
            @Value("${agent_builder_endpoint:}") String agentBuilderEndpoint) {
        DownstreamErrorParser builderParser = new DownstreamErrorParser(
            new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
        return new ClientTemplate(factory,
            new DownstreamClientTemplateErrorHandler(DownstreamService.BUILDER, builderParser),
            new BuilderCorrelationInterceptor(agentBuilderEndpoint),
            // transport failure（连接拒绝/DNS/超时/无响应）→ DownstreamFailureException（BUILDER 身份）
            new ServiceAwareClientHttpRequestInterceptor(DownstreamService.BUILDER, builderParser));
    }
}

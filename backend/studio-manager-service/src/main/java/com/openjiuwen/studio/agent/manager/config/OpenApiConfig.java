/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;

import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI 文档配置
 *
 * <p>配置 springdoc-openapi 全局元数据和接口分组。
 * 兼容 Swagger 2（@Api/@ApiOperation/@ApiModel）和 OpenAPI 3（@Tag/@Operation/@Schema）两套注解，
 * 无需迁移注解即可生成完整 API 文档。</p>
 *
 * <p>文档是否对外暴露由 application-manager.yml 中的 springdoc.api-docs.enabled 和
 * springdoc.swagger-ui.enabled 控制，默认关闭（API_DOCS_ENABLED=false）。
 * 本地开发时设环境变量 API_DOCS_ENABLED=true 即可开启。</p>
 */
@Configuration
public class OpenApiConfig {

    private final InterfaceApiOperationCustomizer interfaceApiOperationCustomizer;

    public OpenApiConfig(InterfaceApiOperationCustomizer interfaceApiOperationCustomizer) {
        this.interfaceApiOperationCustomizer = interfaceApiOperationCustomizer;
    }

    @Bean
    public OpenAPI customOpenApi() {
        return new OpenAPI()
            .info(new Info()
                .title("Agent Studio Manager API")
                .version("v1")
                .description("智能体管理平台 API 文档 — 涵盖智能体创建、配置、发布、知识库管理、提示词工程等管理面接口")
                .contact(new Contact().name("OpenJiuWen Team"))
                .license(new License().name("Apache 2.0")))
            .servers(List.of(
                new Server().url("/").description("当前环境")))
            .components(new Components()
                .addSecuritySchemes("AccessToken",
                    new SecurityScheme()
                        .type(SecurityScheme.Type.APIKEY)
                        .in(SecurityScheme.In.HEADER)
                        .name("Access-Token")
                        .description("SSO 访问令牌，通过请求头 Access-Token 传递；Simple 模式使用 X-Auth-Token")));
    }

    @Bean
    public GroupedOpenApi agentManagementGroup() {
        return GroupedOpenApi.builder()
            .group("agent-management")
            .packagesToScan("com.openjiuwen.studio.agent.manager.controller")
            .addOperationCustomizer(interfaceApiOperationCustomizer)
            .build();
    }

    @Bean
    public GroupedOpenApi promptEngineeringGroup() {
        return GroupedOpenApi.builder()
            .group("prompt-engineering")
            .packagesToScan("com.openjiuwen.studio.prompt.engineering.controller")
            .addOperationCustomizer(interfaceApiOperationCustomizer)
            .build();
    }
}

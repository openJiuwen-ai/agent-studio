/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
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
 * <p>文档默认关闭，仅作为内部开发调试开关，不对外暴露。
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
                .description("智能体管理平台 API 文档 — 涵盖智能体创建、配置、发布、知识库管理、提示词工程等管理面接口。\n\n"
                    + "## 认证说明\n"
                    + "本版本默认启用 Simple 认证（POC/演示模式），请求头 X-Auth-Token 为选填：\n"
                    + "- 不传 X-Auth-Token：自动使用内置默认用户 testUser|0 兜底，适用于本地开发与功能演示；\n"
                    + "- 传入 X-Auth-Token：格式为 userId|projectId（例如 testUser|0），以该用户身份访问。\n"
                    + "Simple 认证不提供真实访问控制，生产环境请通过企业 SSO 鉴权保障安全（需二次开发对接）。\n\n"
                    + "## 响应格式\n"
                    + "接口响应分为两种形态：\n"
                    + "- 直接返回业务对象（各接口响应 schema 即业务数据结构）；\n"
                    + "- 返回统一包装体 {code, message, data}（响应 schema 为 BaseResp / PromptBaseResp 等包装类型），"
                    + "其中 code 为 0 表示业务成功，非 0 表示业务失败，data 为业务数据。")
                .contact(new Contact().name("OpenJiuWen Team"))
                .license(new License().name("Apache 2.0")))
            .servers(List.of(
                new Server().url("/").description("当前环境")));
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

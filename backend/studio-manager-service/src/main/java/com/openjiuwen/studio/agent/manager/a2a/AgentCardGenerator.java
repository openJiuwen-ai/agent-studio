/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.a2a;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.a2a.dto.AgentCardDto;
import com.openjiuwen.studio.agent.common.config.RdcProperties;
import com.openjiuwen.studio.agent.common.constant.Constants;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;

/**
 * Agent Card 生成器
 *
 * <p>FEAT-131: 发布时按应用类型生成 A2A Agent Card 元数据</p>
 * <p>Card 内容唯一来源是应用元数据，与 /.well-known/agent-card.json 同源一致</p>
 */
@Slf4j
@Component
public class AgentCardGenerator {

    private final RdcProperties rdcProperties;

    public AgentCardGenerator(RdcProperties rdcProperties) {
        this.rdcProperties = rdcProperties;
    }

    /**
     * 生成 Agent Card
     *
     * @param agentId 应用 ID（身份不变量，name=agentId）
     * @param description 应用描述
     * @param version 发布版本号
     * @param appType 应用类型（Constants.AppType.AGENT / WORKFLOW / CONTROLLER）
     * @return AgentCardDto，或 null 表示不支持 A2A 暴露
     */
    public AgentCardDto generate(String agentId, String description, String version, String appType) {
        if (!isSupportedAppType(appType)) {
            log.info("App type {} not supported for A2A, agentId={}", appType, agentId);
            return null;
        }

        String endpointUrl = rdcProperties.getRuntimeBaseUrl() + rdcProperties.getEndpointPath();

        AgentCardDto.SupportedInterface supportedInterface = AgentCardDto.SupportedInterface.builder()
            .protocolBinding("JSONRPC")
            .url(endpointUrl)
            .transportType(null)
            .protocolVersion("CURRENT_PROTOCOL_VERSION")
            .build();

        return AgentCardDto.builder()
            .name(agentId)
            .description(description != null ? description : "")
            .version(version)
            .url(endpointUrl)
            .capabilities(AgentCardDto.Capabilities.builder().streaming(true).build())
            .skills(Collections.emptyList())
            .defaultInputModes(List.of("text"))
            .defaultOutputModes(List.of("text"))
            .supportedInterfaces(List.of(supportedInterface))
            .build();
    }

    /**
     * 将 AgentCardDto 序列化为 JSON 字符串
     */
    public String toJson(AgentCardDto card) {
        return JSON.toJSONString(card);
    }

    /**
     * 判断应用类型是否支持 A2A 暴露
     *
     * <p>支持：AGENT / MULTI_AGENTS(=CONTROLLER) / WORKFLOW（含子类型 task/chat）</p>
     * <p>不支持：UNKNOWN 或其他类型</p>
     */
    public boolean isSupportedAppType(String appType) {
        if (appType == null) {
            return false;
        }
        return Constants.AppType.AGENT.equals(appType)
            || Constants.AppType.CONTROLLER.equals(appType)
            || Constants.AppType.WORKFLOW.equals(appType)
            || "task".equals(appType)
            || "chat".equals(appType);
    }
}

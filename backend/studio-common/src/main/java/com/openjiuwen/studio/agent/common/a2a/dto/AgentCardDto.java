/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.a2a.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * A2A Agent Card DTO
 *
 * <p>FEAT-131: 发布时按应用类型生成 Card 元数据</p>
 * <p>字段对齐高码 SDK (RemoteAgentCaller) 预期</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentCardDto {

    /**
     * agentId（与应用 1:1，身份不变量）
     */
    private String name;

    /**
     * 应用描述
     */
    private String description;

    /**
     * 发布版本号
     */
    private String version;

    /**
     * A2A 服务面 JSON-RPC 端点地址
     */
    private String url;

    /**
     * 能力声明
     */
    private Capabilities capabilities;

    /**
     * 技能列表（一期可为空）
     */
    private List<Skill> skills;

    /**
     * 默认输入模式
     */
    private List<String> defaultInputModes;

    /**
     * 默认输出模式
     */
    private List<String> defaultOutputModes;

    /**
     * 支持的接口列表
     */
    private List<SupportedInterface> supportedInterfaces;

    /**
     * 能力声明
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Capabilities {
        private boolean streaming;
    }

    /**
     * 技能
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Skill {
        private String id;
        private String name;
        private String description;
        private List<String> tags;
        private List<String> inputModes;
        private List<String> outputModes;
    }

    /**
     * 支持的接口
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SupportedInterface {
        private String protocolBinding;
        private String url;
        private String transportType;
        private String protocolVersion;
    }
}

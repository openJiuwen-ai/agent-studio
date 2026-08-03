/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 客户 Header Profile 配置 Bean — 对应  YAML 配置
 *
 * <p>YAML 结构示例（扁平，单客户本期约束；无 profile 选择层）：
 * <pre>
 * customer-header:
 *   enabled: true
 *   environment: simple
 *   identity:
 *     user-id-header: cust-userid
 *     token-header: cust-token
 *   capture:
 *     customer-allow: [cust-userid, cust-token]
 *   boundary:
 *     agent-runtime-inbound:
 *       customer-passthrough: [cust-userid, cust-token]
 *   targets:
 *     LAKESEARCH:
 *       mappings: [{from: cust-userid, to: userid}, {from: cust-token, to: token}]
 *     IR_AUTH_KEYS:
 *       forward-list: [cust-userid, cust-token, x-auth-token]
 * </pre>
 */
@Component
@ConfigurationProperties(prefix = "customer-header")
public class CustomerHeaderProfile {

    /** 是否启用客户 Header 引擎 */
    private boolean enabled = false;

    /** 运行环境门控（仅 simple 模式启用身份替代） */
    private String environment;

    /** 身份配置（effective userId） */
    private Identity identity;

    /** 入站捕获白名单 */
    private Capture capture;

    /** boundary 透传名单（manager→下游 原样转发 cust-*） */
    private Boundary boundary;

    /** 下游 Target 投影（rename / forward-list） */
    private Map<String, TargetConfig> targets;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getEnvironment() {
        return environment;
    }

    public void setEnvironment(String environment) {
        this.environment = environment;
    }

    public Identity getIdentity() {
        return identity;
    }

    public void setIdentity(Identity identity) {
        this.identity = identity;
    }

    public Capture getCapture() {
        return capture;
    }

    public void setCapture(Capture capture) {
        this.capture = capture;
    }

    public Boundary getBoundary() {
        return boundary;
    }

    public void setBoundary(Boundary boundary) {
        this.boundary = boundary;
    }

    public Map<String, TargetConfig> getTargets() {
        return targets;
    }

    public void setTargets(Map<String, TargetConfig> targets) {
        this.targets = targets;
    }

    /**
     * 判断是否在 simple 模式下启用（门控）
     *
     * @return enabled 且 environment=simple 时返回 true
     */
    public boolean isEnabledInSimpleMode() {
        return enabled && environment != null && "simple".equalsIgnoreCase(environment);
    }

    /**
     * 获取捕获白名单
     *
     * @return 白名单数组，未启用/未配置返回空数组
     */
    public String[] getCaptureAllowList() {
        if (!enabled || capture == null || capture.getCustomerAllow() == null) {
            return new String[0];
        }
        return capture.getCustomerAllow().toArray(new String[0]);
    }

    /**
     * 获取指定 boundary target 的 customer-passthrough 白名单
     *
     * @param target boundary target（AGENT_RUNTIME_INBOUND / AGENT_BUILDER_INBOUND）
     * @return passthrough 白名单列表，未启用/未配置返回空列表
     */
    public List<String> getBoundaryPassthrough(InternalTarget target) {
        if (!enabled || boundary == null) {
            return new ArrayList<>();
        }
        BoundaryEntry entry = null;
        switch (target) {
            case AGENT_RUNTIME_INBOUND:
                entry = boundary.getAgentRuntimeInbound();
                break;
            case AGENT_BUILDER_INBOUND:
                entry = boundary.getAgentBuilderInbound();
                break;
            default:
                return new ArrayList<>();
        }
        if (entry == null || entry.getCustomerPassthrough() == null) {
            return new ArrayList<>();
        }
        return entry.getCustomerPassthrough();
    }

    /**
     * 获取指定 Target 的 mappings 配置
     *
     * @param target 下游 Target
     * @return mappings 列表，未启用/未配置返回空列表
     */
    public List<Mapping> getTargetMappings(InternalTarget target) {
        if (!enabled || targets == null) {
            return new ArrayList<>();
        }
        TargetConfig config = targets.get(target.name());
        if (config == null || config.getMappings() == null) {
            return new ArrayList<>();
        }
        return config.getMappings();
    }

    /**
     * 获取 IR_AUTH_KEYS 的 forward-list
     *
     * @return forward-list 列表，未启用/未配置返回空列表
     */
    public List<String> getIrAuthKeysForwardList() {
        if (!enabled || targets == null) {
            return new ArrayList<>();
        }
        TargetConfig config = targets.get(InternalTarget.IR_AUTH_KEYS.name());
        if (config == null || config.getForwardList() == null) {
            return new ArrayList<>();
        }
        return config.getForwardList();
    }

    /**
     * 获取 identity.user-id-header（effective userId 查找用）
     *
     * <p>供 SimpleUserContextFilter 计算 effective userId 时按配置 header 名查找，
     * 而非硬编码常量（M8 配置化：新客户只改配置不改代码）。
     * 未启用/未配置 identity 时返回 null。
     *
     * @return user-id-header 名，未配置返回 null
     */
    public String getUserIdHeader() {
        if (!enabled || identity == null) {
            return null;
        }
        return identity.getUserIdHeader();
    }

    // ── 内部配置类 ──

    public static class Identity {
        private String userIdHeader;
        private String tokenHeader;
        private String fallback;

        public String getUserIdHeader() {
            return userIdHeader;
        }

        public void setUserIdHeader(String userIdHeader) {
            this.userIdHeader = userIdHeader;
        }

        public String getTokenHeader() {
            return tokenHeader;
        }

        public void setTokenHeader(String tokenHeader) {
            this.tokenHeader = tokenHeader;
        }

        public String getFallback() {
            return fallback;
        }

        public void setFallback(String fallback) {
            this.fallback = fallback;
        }
    }

    public static class Capture {
        private List<String> customerAllow;

        public List<String> getCustomerAllow() {
            return customerAllow;
        }

        public void setCustomerAllow(List<String> customerAllow) {
            this.customerAllow = customerAllow;
        }
    }

    public static class Boundary {
        private BoundaryEntry agentRuntimeInbound;
        private BoundaryEntry agentBuilderInbound;

        public BoundaryEntry getAgentRuntimeInbound() {
            return agentRuntimeInbound;
        }

        public void setAgentRuntimeInbound(BoundaryEntry agentRuntimeInbound) {
            this.agentRuntimeInbound = agentRuntimeInbound;
        }

        public BoundaryEntry getAgentBuilderInbound() {
            return agentBuilderInbound;
        }

        public void setAgentBuilderInbound(BoundaryEntry agentBuilderInbound) {
            this.agentBuilderInbound = agentBuilderInbound;
        }
    }

    public static class BoundaryEntry {
        private List<String> customerPassthrough;

        public List<String> getCustomerPassthrough() {
            return customerPassthrough;
        }

        public void setCustomerPassthrough(List<String> customerPassthrough) {
            this.customerPassthrough = customerPassthrough;
        }
    }

    public static class TargetConfig {
        private List<Mapping> mappings;
        private List<String> forwardList;

        public List<Mapping> getMappings() {
            return mappings;
        }

        public void setMappings(List<Mapping> mappings) {
            this.mappings = mappings;
        }

        public List<String> getForwardList() {
            return forwardList;
        }

        public void setForwardList(List<String> forwardList) {
            this.forwardList = forwardList;
        }
    }

    public static class Mapping {
        private String from;
        private String to;

        public String getFrom() {
            return from;
        }

        public void setFrom(String from) {
            this.from = from;
        }

        public String getTo() {
            return to;
        }

        public void setTo(String to) {
            this.to = to;
        }
    }
}

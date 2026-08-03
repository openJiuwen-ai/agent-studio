/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Header 投影引擎 — 执行下游 rename/passthrough/forward-list 原语
 *
 * <p>Java 侧引擎处理同进程 Target（如 LakeSearch IR auth_keys）。
 * Python 侧引擎处理跨进程 Target（如 runtime LLM），两侧共享 Schema。
 *
 * <p>每请求每 Target 只投影一次（防双投影）。
 * 保留 header 黑名单强制丢弃。
 */
public class HeaderProjectionEngine {

    private static final Logger log = LoggerFactory.getLogger(HeaderProjectionEngine.class);

    /**
     * 保留 header 黑名单 — 客户捕获值不得生成这些 header
     */
    private static final Set<String> RESERVED_BLACKLIST = Set.of(
        "authorization", "host", "content-length", "transfer-encoding",
        "connection", "via", "max-forwards", "forwarded",
        "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto",
        "x-real-ip", "x-original-url", "x-rewrite-url"
    );

    /**
     * 每请求已投影 Target 追踪（防双投影检测）— 由 {@link #clearProjectionTracking} 清理
     */
    private static final ThreadLocal<Set<InternalTarget>> PROJECTED_TARGETS = new ThreadLocal<>();

    /**
     * 判断 header 名是否为保留名（黑名单）— 含 x-forwarded-* 前缀模式
     *
     * @param name 规范化小写 header 名
     * @return 是否保留
     */
    private static boolean isReservedHeader(String name) {
        if (name == null) {
            return false;
        }
        return RESERVED_BLACKLIST.contains(name) || name.startsWith("x-forwarded-");
    }

    private final CustomerHeaderProfile profile;

    public HeaderProjectionEngine(CustomerHeaderProfile profile) {
        this.profile = profile;
    }

    /**
     * 执行下游 rename 投影 — 将 captured headers 按 Target mappings 改名
     *
     * <p>原语：rename（值不变，只改名）。适用于  LakeSearch runtime LLM 等。
     *
     * @param target   下游 Target（如 LAKESEARCH、RUNTIME_LLM_CHAT）
     * @param captured 捕获的客户 headers
     * @return 投影后的 header 映射（key 为目标名，value 为 header 值）
     */
    public Map<String, String> project(InternalTarget target, CapturedCustomerHeaders captured) {
        return project(target, captured, Map.of());
    }

    /**
     * 执行下游 rename 投影 — 支持附加静态配置 headers
     *
     * @param target          下游 Target
     * @param captured        捕获的客户 headers
     * @param configHeaders   静态配置 headers（如模型自身的认证 header，不参与 rename）
     * @return 投影后的 header 映射
     */
    public Map<String, String> project(InternalTarget target,
                                       CapturedCustomerHeaders captured,
                                       Map<String, String> configHeaders) {
        //  防双投影检测：记录同一请求内已投影的 Target。引擎无状态且每次返回新 Map（幂等），
        // 真正的"防双投影"由幂等性 + 调用方每次出站只合并一次共同保证；此处仅做可检测（debug 级），
        // 不抛异常以支持 LakeSearch 多次检索等同一请求内对同一 Target 的合法多次调用。
        Set<InternalTarget> seen = PROJECTED_TARGETS.get();
        if (seen == null) {
            seen = new HashSet<>();
            PROJECTED_TARGETS.set(seen);
        }
        if (!seen.add(target)) {
            log.debug("[customer-header] Duplicate header projection for target {} in the same request ", target);
        }

        Map<String, String> result = new LinkedHashMap<>();

        // 先放入静态配置 headers
        if (configHeaders != null) {
            for (Map.Entry<String, String> entry : configHeaders.entrySet()) {
                String name = entry.getKey().toLowerCase();
                if (!isReservedHeader(name)) {
                    result.put(name, entry.getValue());
                }
            }
        }

        // 按 Target mappings 执行 rename
        List<CustomerHeaderProfile.Mapping> mappings = profile.getTargetMappings(target);
        for (CustomerHeaderProfile.Mapping mapping : mappings) {
            if (mapping.getFrom() == null || mapping.getTo() == null) {
                continue;
            }
            String fromName = mapping.getFrom().toLowerCase();
            String toName = mapping.getTo();

            // 检查黑名单 — 目标名不得为保留 header
            if (isReservedHeader(toName.toLowerCase())) {
                log.warn("[customer-header] Header projection target '{}' is reserved, skipped for target {}",
                    toName, target);
                continue;
            }

            String value = captured.get(fromName);
            if (value != null && !value.isEmpty()) {
                // 同一目标名已有值且来源不同 → 拒绝（规则3 冲突检测）
                if (result.containsKey(toName) && !result.get(toName).equals(value)) {
                    throw new IllegalStateException(String.format(
                        "Header projection conflict on '%s' for target %s: existing='%s', incoming='%s'",
                        toName, target, result.get(toName), value));
                }
                result.put(toName, value);
            }
        }

        if (!result.isEmpty()) {
            log.debug("[customer-header] Header projection completed: target={}, projectedKeys={}", target, result.keySet());
        }
        return result;
    }

    /**
     * 执行 IR auth_keys forward-list 声明
     *
     * <p>返回 Profile 配置的 forward-list（确定性，不读当次请求存在性）。
     * IR auth_keys 只声明 header 名，不存值。
     *
     * @return forward-list header 名列表
     */
    public List<String> forwardList(InternalTarget target) {
        if (target == InternalTarget.IR_AUTH_KEYS) {
            return profile.getIrAuthKeysForwardList();
        }
        return List.of();
    }

    /**
     * 执行 boundary customer-passthrough
     *
     * <p>将 captured headers 按白名单原样转发到 boundary target。
     *
     * @param target   boundary target（AGENT_RUNTIME_INBOUND / AGENT_BUILDER_INBOUND）
     * @param captured 捕获的客户 headers
     * @return passthrough header 映射（key 为原始名，value 为 HeaderValue）
     */
    public Map<String, HeaderValue> passthrough(InternalTarget target,
                                                 CapturedCustomerHeaders captured) {
        List<String> allowList = profile.getBoundaryPassthrough(target);
        Map<String, HeaderValue> result = new LinkedHashMap<>();
        for (String name : allowList) {
            String value = captured.get(name);
            if (value != null && !value.isEmpty()) {
                HeaderValue hv = captured.asMap().get(name.toLowerCase());
                if (hv != null) {
                    result.put(hv.normalizedName(), hv);
                }
            }
        }
        return result;
    }

    /**
     * 获取保留 header 黑名单
     *
     * @return 不可变黑名单集合
     */
    public static Set<String> getReservedBlacklist() {
        return RESERVED_BLACKLIST;
    }

    /**
     * 清理当前请求的投影追踪状态— 由 {@code RequestContextUtils.remove} 在请求结束/异常时调用
     */
    public static void clearProjectionTracking() {
        PROJECTED_TARGETS.remove();
    }
}

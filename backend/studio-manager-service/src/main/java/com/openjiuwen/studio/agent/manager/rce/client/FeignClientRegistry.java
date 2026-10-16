/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import java.util.Map;
import java.util.Set;

/**
 * Manager 跨服务 Feign 客户端显式治理清单（COM-04 §5.2/§10.4/复审 4.4）。
 *
 * <p>每个 {@code @FeignClient} 必须显式判定为 RUNTIME、BUILDER 或 DENY；治理测试扫描全部
 * {@code @FeignClient}，未登记名返回 {@link Decision#UNCLASSIFIED} 并使测试失败——
 * 新增客户端不登记即不能通过治理，防止绕过目标归属评审。
 *
 * <ul>
 *   <li>{@link Decision#RUNTIME} — 目标 Runtime，按方法级清单区分执行/非执行（{@code agentRuntime}）</li>
 *   <li>{@link Decision#BUILDER} — 目标 Builder，固定 BUILDER 策略（{@code agentBuilder}）</li>
 *   <li>{@link Decision#DENY} — 非白名单或未启用目标，不注入关联 Header</li>
 * </ul>
 *
 * <p>{@code jiuWenService} 标记为 DENY/未启用：该客户端在初始化提交即存在，当前无生产调用方，
 * 仅凭 URL 配置不足以证明启用状态与下游归属；后续启用须独立评审转为 RUNTIME_NON_EXECUTION。
 *
 * <p>Feign 目标 URL 由 {@code @FeignClient(url=...)} 配置绑定，非调用方逐请求可改；运行时由
 * 关联拦截器注入受信任 origin 并经 {@code CorrelationOriginValidator} 校验 {@code feignTarget().url()}
 * 的最终目标（scheme+host+effective port，复审 4.2）——配置为空/非法/与允许 origin 不一致即失败。
 *
 * <p>跨源重定向边界（复审 4.3 / §5.1 §10.2）：ALLOW 客户端在 {@code application-manager.yml}
 * 设置 {@code spring.cloud.openfeign.client.config.<name>.followRedirects: false}（agentRuntime、
 * agentBuilder），3xx 显式失败而非跟随，关联 Header 不会被带到非白名单 origin。该配置与 connect/readTimeout
 * 同属 {@code FeignClientConfiguration}，不替换 Client、不绕过超时配置。流式 OkHttp 路径另用
 * {@code OkHttpCorrelationHeaderApplier#withoutRedirects}。
 */
public final class FeignClientRegistry {

    public enum Decision {
        RUNTIME,
        BUILDER,
        /** 显式拒绝：不注入关联 Header。 */
        DENY,
        /** 未登记——治理测试必须失败，强制显式分类。 */
        UNCLASSIFIED
    }

    private static final Map<String, Decision> DECISIONS = Map.ofEntries(
        // 允许
        Map.entry("agentRuntime", Decision.RUNTIME),
        Map.entry("agentBuilder", Decision.BUILDER),
        // 显式拒绝：未启用或非白名单
        Map.entry("jiuWenService", Decision.DENY),
        Map.entry("agent-builder", Decision.DENY),
        Map.entry("apigClient", Decision.DENY),
        Map.entry("cseClient", Decision.DENY),
        Map.entry("customModelManager", Decision.DENY),
        Map.entry("eipClient", Decision.DENY),
        Map.entry("elbClient", Decision.DENY),
        Map.entry("iamClient", Decision.DENY),
        Map.entry("iamManager", Decision.DENY),
        Map.entry("itepIamClient", Decision.DENY),
        Map.entry("ltsClient", Decision.DENY),
        Map.entry("maasModel", Decision.DENY),
        Map.entry("managementCenterFeignClient", Decision.DENY),
        Map.entry("modelManager", Decision.DENY),
        Map.entry("natClient", Decision.DENY),
        Map.entry("petalSearch", Decision.DENY),
        Map.entry("pythonInterpreter", Decision.DENY),
        Map.entry("swrClient", Decision.DENY),
        Map.entry("vpcClient", Decision.DENY),
        Map.entry("agentBaseRag", Decision.DENY),
        Map.entry("CssUniSearch", Decision.DENY));

    private FeignClientRegistry() {
    }

    /** 客户端名 → 决策；未登记返回 UNCLASSIFIED（治理测试失败）。 */
    public static Decision decisionFor(String clientName) {
        return DECISIONS.getOrDefault(clientName, Decision.UNCLASSIFIED);
    }

    /** 允许注入关联 Header 的客户端名集合（RUNTIME/BUILDER）。 */
    public static Set<String> allowedClients() {
        Set<String> allowed = new java.util.LinkedHashSet<>();
        for (Map.Entry<String, Decision> e : DECISIONS.entrySet()) {
            if (e.getValue() == Decision.RUNTIME || e.getValue() == Decision.BUILDER) {
                allowed.add(e.getKey());
            }
        }
        return allowed;
    }

    /** 全部已显式登记的客户端名（用于治理测试断言扫描结果无遗漏、无陈旧）。 */
    public static Set<String> allClassifiedClients() {
        return DECISIONS.keySet();
    }
}

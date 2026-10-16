/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;

/**
 * Runtime Feign 方法级清单治理测试（COM-04 §6.1/§10.4）。
 *
 * <p>catalog 注释承诺"治理测试扫描全部 @FeignClient，未登记名返回 UNCLASSIFIED 并使测试失败"。
 * 本测试兑现该承诺：枚举 {@link AgentRuntimeClient} 每个接口方法，断言其在
 * {@link AgentRuntimeFeignMethodCatalog#methodPolicies()} 中登记（未登记方法在运行期 resolve()
 * 会抛 IllegalStateException，致生产路径崩溃）；同时断言无陈旧条目（catalog 有、接口无）。
 * 新增 AgentRuntimeClient 方法未登记即测试失败——强制显式分类。
 */
class AgentRuntimeFeignMethodCatalogCoverageTest {

    @Test
    void every_agent_runtime_client_method_is_registered() {
        Map<String, ?> policies = AgentRuntimeFeignMethodCatalog.methodPolicies();
        List<String> unregistered = new ArrayList<>();
        for (Method m : AgentRuntimeClient.class.getDeclaredMethods()) {
            // Object 方法（equals/hashCode/toString 等，@FeignClient 接口通常无，防御）
            if (m.getDeclaringClass() == Object.class) {
                continue;
            }
            if (!policies.containsKey(m.getName())) {
                unregistered.add(m.getName());
            }
        }
        assertThat(unregistered)
            .as("AgentRuntimeClient 方法未在 AgentRuntimeFeignMethodCatalog.METHOD_POLICIES 登记（运行期 resolve() 会抛 IllegalStateException）")
            .isEmpty();
    }

    @Test
    void no_stale_entries_in_catalog() {
        Map<String, ?> policies = AgentRuntimeFeignMethodCatalog.methodPolicies();
        Map<String, ?> registered = java.util.Arrays.stream(AgentRuntimeClient.class.getDeclaredMethods())
            .map(Method::getName)
            .collect(Collectors.toMap(n -> n, n -> n, (a, b) -> a));
        List<String> stale = new ArrayList<>();
        for (String name : new TreeSet<>(policies.keySet())) {
            if (!registered.containsKey(name)) {
                stale.add(name);
            }
        }
        assertThat(stale)
            .as("catalog 中有 AgentRuntimeClient 接口不存在的陈旧条目（接口已变更，catalog 未同步）")
            .isEmpty();
    }

    /**
     * 每个登记方法必须有 mapping 注解（@PostMapping/@GetMapping 等）→ buildRules 生成 RouteRule。
     * 未来方法只加 METHOD_POLICIES 条目、漏 @PostMapping 时，上两测试绿但 resolve() 运行期抛
     * IllegalStateException——正是治理测试应 catch 的回归类别。
     */
    @Test
    void every_registered_method_has_mapping_annotation() {
        Map<String, ?> policies = AgentRuntimeFeignMethodCatalog.methodPolicies();
        Map<String, Method> ifaceMethods = java.util.Arrays.stream(AgentRuntimeClient.class.getDeclaredMethods())
            .collect(Collectors.toMap(Method::getName, m -> m, (a, b) -> a));
        List<String> noMapping = new ArrayList<>();
        for (String name : policies.keySet()) {
            Method m = ifaceMethods.get(name);
            if (m == null) {
                continue;  // 陈旧条目由 no_stale_entries_in_catalog 覆盖
            }
            if (AgentRuntimeFeignMethodCatalog.readMapping(m) == null) {
                noMapping.add(name);
            }
        }
        assertThat(noMapping)
            .as("METHOD_POLICIES 登记的方法缺少 @PostMapping/@GetMapping 等 mapping 注解，buildRules 不生成 RouteRule，resolve() 运行期抛 IllegalStateException")
            .isEmpty();
    }
}

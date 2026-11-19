/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;

import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * #1659/#1727：兼容 GET /metrics → Prometheus 文本（与 /actuator/prometheus 等价）。
 *
 * <p>不用 {@code @ConditionalOnBean(PrometheusMeterRegistry)}：该条件在组件扫描阶段求值，
 * 早于 Micrometer 自动配置注册 Registry，会导致本控制器被跳过、/metrics 一直 404。
 * 改为 {@code @ConditionalOnClass}（类路径判断）+ {@link ObjectProvider} 运行时取 Bean。
 */
@RestController
@ConditionalOnClass(PrometheusMeterRegistry.class)
public class PrometheusMetricsAliasController {

    private final ObjectProvider<PrometheusMeterRegistry> prometheusMeterRegistry;

    public PrometheusMetricsAliasController(ObjectProvider<PrometheusMeterRegistry> prometheusMeterRegistry) {
        this.prometheusMeterRegistry = prometheusMeterRegistry;
    }

    @GetMapping(value = "/metrics", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<String> metrics() {
        PrometheusMeterRegistry registry = prometheusMeterRegistry.getIfAvailable();
        if (registry == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok().contentType(MediaType.TEXT_PLAIN).body(registry.scrape());
    }
}

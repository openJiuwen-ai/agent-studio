/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;

import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * #1659/#1727：兼容 GET /metrics → Prometheus 文本（与 /actuator/prometheus 等价）。
 */
@RestController
@ConditionalOnBean(PrometheusMeterRegistry.class)
public class PrometheusMetricsAliasController {

    private final PrometheusMeterRegistry prometheusMeterRegistry;

    public PrometheusMetricsAliasController(PrometheusMeterRegistry prometheusMeterRegistry) {
        this.prometheusMeterRegistry = prometheusMeterRegistry;
    }

    @GetMapping(value = "/metrics", produces = MediaType.TEXT_PLAIN_VALUE)
    public String metrics() {
        return prometheusMeterRegistry.scrape();
    }
}

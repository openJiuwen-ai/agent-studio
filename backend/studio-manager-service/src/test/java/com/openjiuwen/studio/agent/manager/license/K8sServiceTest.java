/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.license;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.openjiuwen.studio.agent.common.service.K8sRestClient.PodSummary;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

/**
 * 1B 修订后的计算缝测试:原用 client-java CoreV1Api mock,现直接注入
 * PodSummary 列表(不再依赖 io.kubernetes)。
 */
class K8sServiceTest {

    @Test
    void test_getAgentResourceCpu_should_equal_result() {
        K8sService k8sService = new K8sService();
        PodSummary pod = new PodSummary("pod",
                Map.of("group", "agent-builder-agent"), List.of("2"));
        double result = k8sService.getAgentResourceCpu(List.of(pod));
        assertEquals(2, result);
    }

    @Test
    void test_getAgentResourceCpu_millicores_accumulate() {
        K8sService k8sService = new K8sService();
        PodSummary pod = new PodSummary("pod",
                Map.of("app", "jiuwen-runtime"), List.of("500m", "500m"));
        double result = k8sService.getAgentResourceCpu(List.of(pod));
        assertEquals(1.0, result);
    }

    @Test
    void test_getAgentResourceCpu_unmatched_labels_ignored() {
        K8sService k8sService = new K8sService();
        PodSummary pod = new PodSummary("other",
                Map.of("app", "unrelated-app"), List.of("4"));
        assertEquals(0.0, k8sService.getAgentResourceCpu(List.of(pod)));
    }

    @Test
    void test_getAgentResourceCpu_empty_input() {
        assertEquals(0.0, new K8sService().getAgentResourceCpu(List.of()));
    }
}

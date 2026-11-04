/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.license;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.K8sRestClient;
import com.openjiuwen.studio.agent.common.service.K8sRestClient.PodSummary;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * K8s请求(镜像瘦身第一部分 1B 修订,2026-11-04:client-java → K8sRestClient
 * 原生 REST;读侧语义与原实现一致——list pods all namespaces,按标签过滤,
 * 累加各容器 resources.limits.cpu)。
 *
 */
@Component
@Slf4j
public class K8sService {

    private final Set<String> appLabels = Set.of("agent-base-runtime", "agent-console", "agent-manager", "agent-ops",
        "agent-service", "agent-tools", "code-interpreter", "jiuwen-runtime", "agent-builder-agent-manager");

    /**
     * 通过 pod 获取 agent 服务使用的 cpu 资源
     *
     * @return agent 占用 cpu 总数
     */
    public double getAgentResourceCpu() {
        // 暂时不统计 k8s 之外的资源
        if (!K8sRestClient.isRunningInKubernetes()) {
            return 0;
        }
        try {
            return getAgentResourceCpu(K8sRestClient.listPodsAllNamespaces());
        } catch (Exception e) {
            log.error("Get k8s pods error: ", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }

    /**
     * 获取 agent 服务使用的 cpu 资源(注入 pod 概要的计算入口,原
     * getAgentResourceCpu(CoreV1Api) 的等价测试缝)。
     *
     * @param pods 全命名空间 pod 概要(K8sRestClient.listPodsAllNamespaces 产出)
     * @return agent 占用 cpu 总数
     */
    public double getAgentResourceCpu(List<PodSummary> pods) {
        double cpuRequest = 0.0;
        List<String> allPods = new ArrayList<>();
        List<String> agentPods = new ArrayList<>();
        for (PodSummary pod : pods) {
            String podName = pod.getName();
            allPods.add(podName);
            if (pod.getLabels().isEmpty()) {
                continue;
            }
            String appLabel = pod.getLabels().get("app");
            String groupLabel = pod.getLabels().get("group");
            if (!(appLabel != null && appLabels.contains(appLabel)
                    || ("agent-builder-agent".equals(groupLabel)))) {
                continue;
            }
            agentPods.add(podName);
            for (String cpuLimit : pod.getContainerCpuLimits()) {
                cpuRequest += K8sRestClient.parseCpu(cpuLimit);
            }
        }
        log.info("[K8s Resources]:All pods:{}", allPods);
        log.info("[K8s Resources]:Agent pods:{}", agentPods);
        return cpuRequest;
    }
}

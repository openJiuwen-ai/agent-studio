/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.telemetry;

import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;

import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.common.AttributesBuilder;
import io.opentelemetry.api.logs.Logger;
import io.opentelemetry.api.logs.Severity;
import io.opentelemetry.exporter.otlp.http.logs.OtlpHttpLogRecordExporter;
import io.opentelemetry.exporter.otlp.logs.OtlpGrpcLogRecordExporter;
import io.opentelemetry.sdk.logs.SdkLoggerProvider;
import io.opentelemetry.sdk.logs.export.BatchLogRecordProcessor;
import io.opentelemetry.sdk.logs.export.LogRecordExporter;
import io.opentelemetry.sdk.resources.Resource;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * agent 定义态遥测上报服务（OTLP logs 单通道）。
 *
 * <p>两类记录共用同一通道，通过 body 区分：
 * <ul>
 *     <li>生命周期事件（agent.created / updated / published / deleted）：业务写入口触发，精确时间戳；</li>
 *     <li>清单快照心跳（agent.snapshot / agent.snapshot.empty）：定时任务每周期重读 DB 全量存量，
 *     作为当前态快照与对账依据——事件丢失时下一周期快照自动修复。</li>
 * </ul>
 *
 * <p>开关默认关闭（studio.agentTelemetry.switch=false），关闭时零行为变化；
 * 任何上报失败仅记录告警日志，绝不影响业务流程。
 */
@Component
@Slf4j
public class AgentTelemetryService {

    public static final String EVENT_CREATED = "created";

    public static final String EVENT_UPDATED = "updated";

    public static final String EVENT_PUBLISHED = "published";

    public static final String EVENT_DELETED = "deleted";

    private static final String BODY_EVENT_PREFIX = "agent.";

    private static final String BODY_SNAPSHOT = "agent.snapshot";

    private static final String BODY_SNAPSHOT_EMPTY = "agent.snapshot.empty";

    private static final String HTTP_LOGS_PATH = "/v1/logs";

    /**
     * 属性值安全长度上限，避免超长 description 撑爆单条记录
     */
    private static final int MAX_ATTR_LENGTH = 1024;

    private static final DateTimeFormatter ISO_FORMATTER =
        DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneId.of("UTC"));

    @Value("${studio.agentTelemetry.switch:false}")
    private boolean enabled;

    @Value("${studio.agentTelemetry.endpoint:http://localhost:4317}")
    private String endpoint;

    @Value("${studio.agentTelemetry.protocol:grpc}")
    private String protocol;

    @Value("${studio.agentTelemetry.serviceName:agent-studio}")
    private String serviceName;

    private volatile SdkLoggerProvider loggerProvider;

    private volatile Logger otelLogger;

    private final AtomicBoolean initFailed = new AtomicBoolean(false);

    public boolean isEnabled() {
        return enabled;
    }

    /**
     * 发送一条生命周期事件（created / updated / published / deleted）
     *
     * @param eventType 事件类型
     * @param projectId 归属项目
     * @param workspaceId 归属工作空间
     * @param info 写操作返回的 agent 最新信息
     * @param operator 操作人
     */
    public void emitEvent(String eventType, String projectId, String workspaceId, AgentInfo info,
        String operator) {
        if (!enabled || info == null) {
            return;
        }
        AttributesBuilder builder = Attributes.builder()
            .put("openjiuwen.event.type", eventType)
            .put("openjiuwen.agent.id", StringUtils.defaultString(info.getAgentId()))
            .put("openjiuwen.agent.name", truncate(info.getName()))
            .put("openjiuwen.agent.description", truncate(info.getDescription()))
            .put("openjiuwen.agent.status", StringUtils.defaultString(info.getStatus()))
            .put("openjiuwen.agent.type", StringUtils.defaultString(info.getType()))
            .put("openjiuwen.agent.model.name", StringUtils.defaultString(info.getModelName()))
            .put("openjiuwen.agent.model.type", StringUtils.defaultString(info.getModelType()))
            .put("openjiuwen.agent.creator", StringUtils.defaultString(info.getCreator()))
            .put("openjiuwen.event.operator", StringUtils.defaultString(operator));
        if (StringUtils.isNotBlank(projectId)) {
            builder.put("openjiuwen.project.id", projectId);
        } else if (info.getProjectId() != null) {
            builder.put("openjiuwen.project.id", info.getProjectId());
        }
        if (StringUtils.isNotBlank(workspaceId)) {
            builder.put("openjiuwen.workspace.id", workspaceId);
        }
        emit(BODY_EVENT_PREFIX + eventType, builder.build());
    }

    /**
     * 发送一条删除事件。删除发生在落库之后，实体可能已不可查，属性来自删除前捕获的实体。
     *
     * @param capturedAgent 删除前捕获的 agent 实体（可能为 null）
     * @param projectId 归属项目
     * @param workspaceId 归属工作空间
     * @param agentId agentId
     * @param operator 操作人
     */
    public void emitDeletedEvent(Agent capturedAgent, String projectId, String workspaceId, String agentId,
        String operator) {
        if (!enabled) {
            return;
        }
        AttributesBuilder builder = Attributes.builder()
            .put("openjiuwen.event.type", EVENT_DELETED)
            .put("openjiuwen.agent.id", StringUtils.defaultString(agentId))
            .put("openjiuwen.event.operator", StringUtils.defaultString(operator));
        if (StringUtils.isNotBlank(projectId)) {
            builder.put("openjiuwen.project.id", projectId);
        }
        if (StringUtils.isNotBlank(workspaceId)) {
            builder.put("openjiuwen.workspace.id", workspaceId);
        }
        if (capturedAgent != null) {
            builder.put("openjiuwen.agent.name", truncate(capturedAgent.getName()))
                .put("openjiuwen.agent.description", truncate(capturedAgent.getDescription()))
                .put("openjiuwen.agent.status", StringUtils.defaultString(capturedAgent.getStatus()))
                .put("openjiuwen.agent.type", StringUtils.defaultString(capturedAgent.getType()))
                .put("openjiuwen.agent.model.name", StringUtils.defaultString(capturedAgent.getModelName()))
                .put("openjiuwen.agent.model.type", StringUtils.defaultString(capturedAgent.getModelType()))
                .put("openjiuwen.agent.creator", StringUtils.defaultString(capturedAgent.getCreator()));
        }
        emit(BODY_EVENT_PREFIX + EVENT_DELETED, builder.build());
    }

    /**
     * 发送清单快照心跳：逐 agent 一条 snapshot 记录；空清单时发送一条 0 计数心跳，
     * 用于区分“没有 agent”与“服务不可用”。
     *
     * @param agents DB 当前全量在册 agent
     */
    public void emitSnapshot(List<Agent> agents) {
        if (!enabled) {
            return;
        }
        if (agents == null || agents.isEmpty()) {
            emit(BODY_SNAPSHOT_EMPTY, Attributes.builder()
                .put("openjiuwen.agent.count", 0L)
                .build());
            return;
        }
        for (Agent agent : agents) {
            AttributesBuilder builder = Attributes.builder()
                .put("openjiuwen.agent.id", StringUtils.defaultString(agent.getAgentId()))
                .put("openjiuwen.agent.name", truncate(agent.getName()))
                .put("openjiuwen.agent.description", truncate(agent.getDescription()))
                .put("openjiuwen.agent.status", StringUtils.defaultString(agent.getStatus()))
                .put("openjiuwen.agent.type", StringUtils.defaultString(agent.getType()))
                .put("openjiuwen.agent.model.name", StringUtils.defaultString(agent.getModelName()))
                .put("openjiuwen.agent.model.type", StringUtils.defaultString(agent.getModelType()))
                .put("openjiuwen.agent.creator", StringUtils.defaultString(agent.getCreator()))
                .put("openjiuwen.project.id", StringUtils.defaultString(agent.getProjectId()))
                .put("openjiuwen.workspace.id", StringUtils.defaultString(agent.getWorkspaceId()));
            if (agent.getUpdatedOn() != null) {
                builder.put("openjiuwen.agent.updated_on", ISO_FORMATTER.format(agent.getUpdatedOn().toInstant()));
            }
            emit(BODY_SNAPSHOT, builder.build());
        }
    }

    private void emit(String body, Attributes attributes) {
        try {
            Logger logger = otelLogger;
            if (logger == null) {
                init();
                logger = otelLogger;
            }
            if (logger == null) {
                return;
            }
            logger.logRecordBuilder()
                .setBody(body)
                .setSeverity(Severity.INFO)
                .setAllAttributes(attributes)
                .setTimestamp(Instant.now())
                .emit();
        } catch (Exception e) {
            log.warn("agent telemetry emit failed: {}", e.getMessage());
        }
    }

    private synchronized void init() {
        if (otelLogger != null || initFailed.get()) {
            return;
        }
        try {
            LogRecordExporter exporter;
            if ("http".equalsIgnoreCase(protocol)) {
                exporter = OtlpHttpLogRecordExporter.builder()
                    .setEndpoint(httpEndpoint())
                    .build();
            } else {
                exporter = OtlpGrpcLogRecordExporter.builder()
                    .setEndpoint(endpoint)
                    .build();
            }
            Resource resource = Resource.getDefault().merge(Resource.builder()
                .put("service.name", serviceName)
                .put("service.namespace", "agent-studio")
                .build());
            loggerProvider = SdkLoggerProvider.builder()
                .setResource(resource)
                .addLogRecordProcessor(BatchLogRecordProcessor.builder(exporter)
                    .setScheduleDelay(Duration.ofSeconds(5))
                    .build())
                .build();
            otelLogger = loggerProvider.get("com.openjiuwen.studio.agent.telemetry");
            log.info("agent telemetry initialized, endpoint={}, protocol={}", endpoint, protocol);
        } catch (Exception e) {
            initFailed.set(true);
            log.warn("agent telemetry init failed, reporting disabled: {}", e.getMessage());
        }
    }

    private String httpEndpoint() {
        String url = endpoint == null ? "" : endpoint.trim();
        if (url.endsWith(HTTP_LOGS_PATH)) {
            return url;
        }
        return url.replaceAll("/+$", "") + HTTP_LOGS_PATH;
    }

    private String truncate(String value) {
        if (value == null) {
            return "";
        }
        return value.length() <= MAX_ATTR_LENGTH ? value : value.substring(0, MAX_ATTR_LENGTH);
    }

    @PreDestroy
    public void shutdown() {
        SdkLoggerProvider provider = loggerProvider;
        if (provider != null) {
            try {
                provider.close();
            } catch (Exception e) {
                log.warn("agent telemetry shutdown failed: {}", e.getMessage());
            }
        }
    }
}

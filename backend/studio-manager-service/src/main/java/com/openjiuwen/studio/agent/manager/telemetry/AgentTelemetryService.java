/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.telemetry;

import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.McpServerReference;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.manager.rce.models.assistant.KnowledgeRepoListRsp;
import com.openjiuwen.studio.agent.manager.service.RelationManagementService;

import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.common.AttributesBuilder;
import io.opentelemetry.api.logs.Logger;
import io.opentelemetry.api.logs.Severity;
import io.opentelemetry.exporter.otlp.http.logs.OtlpHttpLogRecordExporter;
import io.opentelemetry.exporter.otlp.logs.OtlpGrpcLogRecordExporter;
import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.sdk.logs.SdkLoggerProvider;
import io.opentelemetry.sdk.logs.export.BatchLogRecordProcessor;
import io.opentelemetry.sdk.logs.export.LogRecordExporter;
import io.opentelemetry.sdk.resources.Resource;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Date;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * agent 定义态遥测上报服务（OTLP logs 单通道）。
 *
 * <p>三类记录共用同一通道，通过 body 区分：
 * <ul>
 *     <li>生命周期事件（agent.created / updated / published / deleted）：业务写入口触发，精确时间戳，
 *     携带 DB 时间戳（updated_on / published_on）与脱敏摘要（删除事件含知识库 / 工具 / MCP 清单）；</li>
 *     <li>聚合轻心跳（agent.heartbeat）：定时任务每周期发送一条在册数 + 漂移令牌记录，兼作存活信号；</li>
 *     <li>清单快照（agent.snapshot）：漂移触发 / 低频兜底的全量逐 agent 记录——事件丢失时自愈修复。</li>
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

    private static final String BODY_HEARTBEAT = "agent.heartbeat";

    private static final String HTTP_LOGS_PATH = "/v1/logs";

    /**
     * 属性值安全长度上限，避免超长 description 撑爆单条记录
     */
    private static final int MAX_ATTR_LENGTH = 1024;

    /**
     * 删除事件摘要（知识库 / 工具 / MCP 清单）的最大条目数，防止异常数据撑爆属性
     */
    private static final int MAX_SUMMARY_ENTRIES = 50;

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

    @Autowired
    private RelationManagementService relationManagementService;

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
        putTimestamp(builder, "openjiuwen.agent.updated_on", info.getUpdateTime());
        putTimestamp(builder, "openjiuwen.agent.published_on", info.getPublishTime());
        emit(BODY_EVENT_PREFIX + eventType, builder.build());
    }

    /**
     * 发送一条删除事件。删除为硬删（行 / 版本 / OBS 文件均清理），删除后定义态不可再查，
     * 属性来自删除前捕获的实体，并附带知识库 / 工具 / MCP 的脱敏清单（仅 id 与名称，
     * 不含参数与鉴权原文）作为该 agent 的最后一份配置摘要。
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
            putTimestamp(builder, "openjiuwen.agent.updated_on", capturedAgent.getUpdatedOn());
            putTimestamp(builder, "openjiuwen.agent.published_on", capturedAgent.getPublishedOn());
        }
        appendDeletedSummaries(builder, projectId, workspaceId, agentId);
        emit(BODY_EVENT_PREFIX + EVENT_DELETED, builder.build());
    }

    /**
     * 删除事件的脱敏摘要：知识库 / 工具 / MCP 仅取 id 与名称。任何一项查询失败只影响该项，
     * 不影响事件本身发出。
     */
    private void appendDeletedSummaries(AttributesBuilder builder, String projectId, String workspaceId,
        String agentId) {
        if (StringUtils.isBlank(agentId)) {
            return;
        }
        try {
            KnowledgeRepoListRsp repoRsp =
                relationManagementService.listAgentKnowledge(projectId, workspaceId, agentId, 0, MAX_SUMMARY_ENTRIES);
            if (repoRsp != null && repoRsp.getKnowledgeRepoEntityList() != null) {
                String repos = repoRsp.getKnowledgeRepoEntityList().stream()
                    .limit(MAX_SUMMARY_ENTRIES)
                    .map(r -> StringUtils.defaultString(r.getKnowledgeRepoId()) + ","
                        + StringUtils.defaultString(r.getDisplayName()))
                    .reduce((a, b) -> a + ";" + b)
                    .orElse("");
                builder.put("openjiuwen.agent.knowledge.repos", truncate(repos));
            }
        } catch (Exception e) {
            log.warn("agent telemetry: summary of knowledge repos failed: {}", e.getMessage());
        }
        try {
            List<ToolReference> tools =
                relationManagementService.listAgentTools(projectId, workspaceId, agentId, 0, MAX_SUMMARY_ENTRIES);
            if (tools != null && !tools.isEmpty()) {
                String names = tools.stream()
                    .limit(MAX_SUMMARY_ENTRIES)
                    .map(t -> StringUtils.defaultIfBlank(t.getToolDisplayName(),
                        StringUtils.defaultString(t.getPluginDisplayName())))
                    .reduce((a, b) -> a + ";" + b)
                    .orElse("");
                builder.put("openjiuwen.agent.tools", truncate(names));
            }
        } catch (Exception e) {
            log.warn("agent telemetry: summary of tools failed: {}", e.getMessage());
        }
        try {
            List<McpServerReference> mcpServers = relationManagementService.listAgentMcpServers(agentId);
            if (mcpServers != null && !mcpServers.isEmpty()) {
                String servers = mcpServers.stream()
                    .limit(MAX_SUMMARY_ENTRIES)
                    .map(m -> StringUtils.defaultString(m.getMcpServerName())
                        + "(" + (m.getToolsNum() == null ? 0 : m.getToolsNum()) + ")")
                    .reduce((a, b) -> a + ";" + b)
                    .orElse("");
                builder.put("openjiuwen.agent.mcp.servers", truncate(servers));
            }
        } catch (Exception e) {
            log.warn("agent telemetry: summary of mcp servers failed: {}", e.getMessage());
        }
    }

    /**
     * 发送一条聚合轻心跳：在册 agent 数 + 漂移令牌（最后修改时间），每周期一条，
     * 兼作存活信号（区分"没有 agent"与"服务不可用"）。
     *
     * @param count DB 当前在册 agent 数
     * @param maxUpdatedOn DB 当前 MAX(updated_on) 的字符串形态（空表传空串）
     */
    public void emitHeartbeat(long count, String maxUpdatedOn) {
        if (!enabled) {
            return;
        }
        AttributesBuilder builder = Attributes.builder()
            .put("openjiuwen.agent.count", count);
        if (StringUtils.isNotBlank(maxUpdatedOn)) {
            builder.put("openjiuwen.agent.max_updated_on", maxUpdatedOn);
        }
        emit(BODY_HEARTBEAT, builder.build());
    }

    /**
     * 等待已入队的遥测记录完成一次导出。全量快照发送后调用，仅当导出成功才允许调用方推进
     * 漂移基线（对齐 K8s workqueue 语义：失败即视为未完成，下一周期自然重试）。
     */
    public boolean flushConfirmed() {
        SdkLoggerProvider provider = loggerProvider;
        if (provider == null) {
            return false;
        }
        try {
            CompletableResultCode code = provider.forceFlush();
            code.join(10, java.util.concurrent.TimeUnit.SECONDS);
            return code.isSuccess();
        } catch (Exception e) {
            log.warn("agent telemetry flush failed: {}", e.getMessage());
            return false;
        }
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

    private void putTimestamp(AttributesBuilder builder, String key, Date value) {
        if (value != null) {
            builder.put(key, ISO_FORMATTER.format(value.toInstant()));
        }
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

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure.adapter;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillDescriptor;
import com.openjiuwen.studio.conversation.application.dto.SendMessageCmd;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.repository.ConversationRepository;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;

import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.sse.EventSources;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * 运行时防腐层（ACL）：封装对 runtime 运行链路的调用（团队对话端点）、引擎 SSE 事件 → 领域消息转换与落库。
 *
 * <p>团队对话（Phase 5）：直传团队参数（conversationId + subAgentIds + modelDeploymentId + conversationHistory）
 * 到 runtime 新端点 → 引擎 /v1/conversation/team。引擎按 subAgentIds 加载各子 Agent 已有 IR 动态组装监督者，
 * 不再预烘焙 IR（方案 B，F4：监督者提示词固定引擎侧，Java 不传 systemPrompt）。</p>
 *
 * <p>execution_id：每轮由调用方生成（X-Execution-Id 请求头），引擎事件原样携带，run/sub_run 分组精确。</p>
 */
@Slf4j
@Component
public class AgentRuntimeAdapter {

    private static final long SSE_TIMEOUT = 900_000L;
    private static final long CONNECT_TIMEOUT_SECONDS = 30L;

    @Value("${agent_runtime_endpoint:http://127.0.0.1:31014}")
    private String runtimeEndpoint;

    /** 团队子 Agent ID 列表（内置常量，POC：团队变更时改此处，不再走 yml 配置） */
    private static final String TEAM_AGENT_IDS =
        "d321fa88-a768-4b63-8d68-13cd743c6903,8dafdc64-2c52-40b5-9b24-49894314b763";

    private final ConversationRepository conversationRepository;
    private final OkHttpClientUtils okHttpClientUtils;
    private final ObjectMapper objectMapper;

    public AgentRuntimeAdapter(ConversationRepository conversationRepository,
                               OkHttpClientUtils okHttpClientUtils,
                               ObjectMapper objectMapper) {
        this.conversationRepository = conversationRepository;
        this.okHttpClientUtils = okHttpClientUtils;
        this.objectMapper = objectMapper;
    }

    /**
     * 发起一轮对话运行（SSE 流式返回；事件缓冲到整轮结束一次性落库）
     *
     * @param conversation   会话聚合
     * @param cmd            发送消息命令（query/model_deployment_id）
     * @param histories      全量历史（平台 Message 列表，经 histories 钩子注入引擎）
     * @param executionId    本轮 execution_id（调用方生成，随 X-Execution-Id 请求头下发）
     * @param requestHeaders 当前请求头（转发给 runtime，认证所需的 X-Auth-Token 由 IAM 上下文补齐）
     * @return SSE 流
     */
    public SseEmitter run(Conversation conversation, SendMessageCmd cmd, List<Message> histories,
                          ConversationSkillContext skillContext, String executionId, HttpHeaders requestHeaders) {
        // 直传团队参数（方案 B）：引擎按 subAgentIds 加载各子 Agent 已有 IR 动态组装监督者，不再预烘焙 IR
        String url = buildTeamUrl(conversation);

        Map<String, Object> body = buildRequestBody(conversation, cmd, histories, skillContext);

        Request.Builder builder = new Request.Builder()
            .url(url)
            .post(RequestBody.create(toJson(body), MediaType.parse("application/json; charset=utf-8")));
        copyRequestHeaders(builder, requestHeaders);
        builder.addHeader("X-Execution-Id", executionId);

        // SseEmitter 是 Spring MVC 提供的一个组件，用于在 HTTP 协议上实现 SSE（Server-Sent Events，服务器发送事件），即服务器向浏览器/客户端单向、持续、流式地推送数据。
        SseEmitter sseEmitter = new SseEmitter(SSE_TIMEOUT);

        CountDownLatch latch = new CountDownLatch(1);
        EventSources.createFactory(okHttpClientUtils.getHttpClient())
            .newEventSource(builder.build(),
                new ConversationRunEventSourceListener(sseEmitter, latch, conversation.getConversationId(),
                    executionId, cmd.getModelDeploymentId(), conversationRepository));
        try {
            latch.await(CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Interrupted while waiting conversation run stream connect.", e);
        }
        log.debug("Conversation run stream started: conversationId={}, executionId={}",
            conversation.getConversationId(), executionId);
        return sseEmitter;
    }

    /**
     * 把当前请求头转发给 runtime（manager 统一模式，参照 AgentServiceProxyService.stream），
     * 并补齐 runtime 认证所需 X-Auth-Token（POC 模式按 userId|projectId 解析，取自 IAM 上下文）。
     */
    void copyRequestHeaders(Request.Builder builder, HttpHeaders requestHeaders) {
        requestHeaders.forEach((key, value) -> {
            // X-Auth-Token 以 IAM 上下文为准，跳过外部传入值，避免重复头
            if (CommonConstant.X_AUTH_TOKEN.equalsIgnoreCase(key) || value == null || value.isEmpty()) {
                return;
            }
            builder.addHeader(key, String.join(",", value));
        });
        builder.addHeader(CommonConstant.X_AUTH_TOKEN, RequestContextUtils.getRequestAuthToken());
    }

    /**
     * 引擎团队对话端点 URL（2026-08-12 直连，dev 架构已移除 Java runtime 层）：
     * {endpoint}/v1/conversation/team。conversationId 随请求体下发（引擎契约）。
     * 独立方法便于单测断言 URL 形态（okhttp 异常消息会截断 URL，不能靠异常消息验证）。
     */
    String buildTeamUrl(Conversation conversation) {
        return runtimeEndpoint + "/v1/conversation/team";
    }

    /**
     * 引擎团队请求体（2026-08-12 直连后 conversationId 必须随 body 下发——引擎契约，原先由 runtime
     * 转发层从 URL path 补）。方案 B 直传团队参数，无 systemPrompt（监督者提示词固定引擎侧）。
     */
    Map<String, Object> buildRequestBody(Conversation conversation, SendMessageCmd cmd, List<Message> histories,
                                         ConversationSkillContext skillContext) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("conversationId", conversation.getConversationId());
        body.put("query", cmd.getQuery());
        String selectType = StringUtils.defaultIfBlank(cmd.getSelectType(), "SUPERVISOR");
        body.put("selectType", selectType);
        if ("APP".equals(selectType)) {
            // APP 路径：用户应用互斥字段，只传 appId；模型来自应用自身 IR
            body.put("appId", cmd.getAppId());
        } else {
            body.put("subAgentIds", parseTeamAgentIds(TEAM_AGENT_IDS));
            body.put("modelDeploymentId", cmd.getModelDeploymentId());
        }
        // conversationHistory 显式转 [{role, content}]（引擎契约，容忍 dict；仅监督者注入，子 Agent 不感知）
        body.put("conversationHistory", toHistoryMaps(histories));
        if (cmd.getFileIds() != null && !cmd.getFileIds().isEmpty()) {
            body.put("fileIds", cmd.getFileIds());
        }
        appendSkillContext(body, skillContext);
        return body;
    }

    private void appendSkillContext(Map<String, Object> body, ConversationSkillContext skillContext) {
        ConversationSkillContext trustedContext = skillContext == null ? ConversationSkillContext.empty() : skillContext;
        List<Map<String, String>> skillCatalog = trustedContext.getCatalog().stream()
            .map(this::toSkillCatalogItem)
            .toList();
        body.put("skillCatalog", skillCatalog);
        body.put("recommendedSkillIds", trustedContext.getRecommendedSkillIds());
    }

    private Map<String, String> toSkillCatalogItem(ConversationSkillDescriptor descriptor) {
        Map<String, String> item = new LinkedHashMap<>();
        item.put("skillId", descriptor.getSkillId());
        item.put("versionId", descriptor.getVersionId());
        item.put("name", descriptor.getName());
        item.put("description", descriptor.getDescription());
        item.put("objectKey", descriptor.getObjectKey());
        return item;
    }

    private List<String> parseTeamAgentIds(String idsStr) {
        if (StringUtils.isBlank(idsStr)) {
            return Collections.emptyList();
        }
        return Arrays.stream(idsStr.split(","))
            .map(String::trim)
            .filter(StringUtils::isNotBlank)
            .toList();
    }

    /**
     * 把平台 Message 历史转成引擎契约的 [{role, content}]（显式转换，避免跨服务反序列化类型坑）；
     * 空/全空返回 null（引擎 conversationHistory 缺省 None，第一轮不注入）。
     */
    private List<Map<String, String>> toHistoryMaps(List<Message> histories) {
        if (histories == null || histories.isEmpty()) {
            return null;
        }
        List<Map<String, String>> result = histories.stream()
            .filter(m -> m.getRole() != null || m.getContent() != null)
            .map(m -> {
                Map<String, String> map = new LinkedHashMap<>();
                map.put("role", m.getRole());
                if (m.getContent() != null) {
                    map.put("content", m.getContent());
                }
                return map;
            })
            .toList();
        return result.isEmpty() ? null : result;
    }

    private String toJson(Object body) {
        try {
            return objectMapper.writeValueAsString(body);
        } catch (Exception e) {
            log.error("Failed to serialize conversation run request body.", e);
            return "{}";
        }
    }
}

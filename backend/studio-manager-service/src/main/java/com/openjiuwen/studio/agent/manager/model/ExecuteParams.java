/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.manager.dto.Conversation;

import lombok.Builder;
import lombok.Data;

import org.springframework.http.HttpHeaders;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Future;

/**
 * 工作流运行参数
 *
 */
@Builder
@Data
public class ExecuteParams {
    private String workflowId;

    private String instId;

    /**
     * 执行Agent的租户id
     */
    private String domainId;

    private String projectId;

    private String workspaceId;

    /**
     * 工作流OBS IR路径
     */
    private String irPath;

    private String userId;

    private String inputsUserId;

    private Map<String, Object> inputs;


    private List<String> workflowSequence;

    private List<String> activeWorkflows;

    // 会话历史写入
    private boolean enableHistory;

    // 是否流式接口
    private boolean stream;

    // 是否debug接口
    private boolean debug;

    // 是否上报AgentOps调用数据
    private boolean trace;

    private String traceMode;

    // 是否是百宝箱访问
    private boolean isTreasure;

    // 是否是最新版本
    private boolean isLatestPublish;

    private String parentInstId;

    private String conversationId;

    private Long version;

    private String nodeId;

    private int dialogueCount;

    // 标识是否是单节点调试模式
    private boolean isNodeExecute;

    private String releasedVersion;

    private Long startTime;

    // 标识大模型节点是否流式输出
    private boolean textChunk;

    @Builder.Default
    private Map<String, StringBuilder> messageMap = new HashMap<>();

    private boolean done;

    // 是否主动取消了
    private boolean canceled;

    private HttpHeaders httpHeaders;

    /**
     * 请求id
     */
    private String requestId;

    @Builder.Default
    private boolean isAgent = false;

    @Builder.Default
    // 时间记录
    private Map<String, Long> timeRecord = new ConcurrentHashMap<>();

    // 是否执行成功，0表示成功，-1表示失败
    @Builder.Default
    private int success = 0;

    /**
     * 对话消息列表
     */
    @Builder.Default
    private List<Message> messages = new ArrayList<>();

    @Builder.Default
    private AsyncTaskParamHolder asyncTaskParamHolder = null;

    private Future<?> heartbeatFuture;

    /**
     * 盘古助手侧会话记忆
     */
    @Builder.Default
    private Conversation conversation = null;

    private String environmentId;

    /**
     * 是否老会话，只有新建的会话才上报到AgentOps
     */
    private boolean oldConversation;

    private String ownerProjectId;

    private String ownerWorkspaceId;

    private String ownerDomainId;

    /**
     * 对话id
     */
    private String executionId;

    /**
     * 是否为网页发布调用
     */
    @Builder.Default
    private boolean isWebPage = false;
}

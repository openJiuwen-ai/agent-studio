/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model;

import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.manager.dto.LongTermMemoryRuntime;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.manager.enums.AgentIrType;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionDetailModel;
import com.openjiuwen.studio.agent.manager.model.memory.UserCachedChatTurn;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 执行知识型Agent需要的参数
 *
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentExecuteParams {
    /**
     * 待执行的知识型agent id
     */
    private String agentId;

    /**
     * 会话id
     */
    private String conversationId;

    /**
     * 对话id
     */
    private String executionId;

    /**
     * 执行Agent的租户id
     */
    private String domainId;

    /**
     * 执行Agent的租户项目id
     */
    private String projectId;

    /**
     * 执行Agent的空间id
     */
    private String workspaceId;

    /**
     * 记忆库id
     */
    private String memoryRepoId;

    /**
     * ir OBS路径
     */
    private String irPath;

    /**
     * 问题输入
     */
    private String query;

    /**
     * 控制器输入
     */
    private Map<String, Object> inputs;

    /**
     * agent运行时对应的模型deployment_id
     */
    private String modelDeploymentId;

    /**
     * 请求类型，判断运行场景，分为DEBUG（管理页面调试）和PUBLISHED（百宝箱运行）
     */
    private String type;

    /**
     * 会话是否结束
     */
    private boolean isDone;

    /**
     * 是否开启会话历史
     */
    @Builder.Default
    private boolean isHistoryEnabled = true;

    /**
     * 会话历史交由调用方管理, 传入的历史会话列表
     */
    private List<Message> histories;

    /**
     * 当前轮次的对话信息
     */
    private UserCachedChatTurn chatTurn;

    private boolean isChatTurnAdded;

    /**
     * 用户记忆控制参数
     */
    private LongTermMemoryRuntime longTermMemoryRuntime;

    /**
     * 会话是否取消
     */
    private boolean canceled;

    /**
     * 记忆参数列表，提取插件入参
     */
    private List<MemoryVariable> memoryVariables;

    /**
     * 用户id
     */
    private String userId;

    /**
     * 插件调用入参Map
     */
    @Builder.Default
    private Map<String, String> pluginInputMap = new HashMap<>();

    /**
     * 是否开启插件
     */
    private Map<String, Boolean> toolSwitchDict;

    /**
     * 执行类型
     */
    private String executeType;

    private CompletableFuture<?> heartbeatFuture;

    /**
     * 当前插件调用是否是workflow
     */
    private boolean isWorkflow;

    /**
     * 当前插件调用是否是Mcp服务
     */
    private boolean isMcp;

    /**
     * 执行agent开始时间
     */
    private long startTime;

    /**
     * Agent发布版本号
     */
    private String versionId;

    /**
     * 请求id
     */
    private String requestId;

    private String taskId;

    @Builder.Default
    // 时间记录
    private Map<String, Long> timeRecord = new ConcurrentHashMap<>();

    // 是否执行成功，0表示成功，-1表示失败
    @Builder.Default
    private int success = 0;

    /**
     * RequestAuthToken
     */
    private String token;

    /**
     * true：返回node_info，内容为多Agent场景下工作流节点详情；false：不返回node_info
     */
    private boolean debug;

    /**
     * 上报AgentOps开关
     */
    private boolean uploadOpsSwitch;

    private String traceMode;

    /**
     * 对话消息列表
     */
    private List<Message> messages;

    /**
     * 控制器消息列表
     */
    private List<Message> controllerMessages;

    /**
     * true：最新发布版本
     */
    @Builder.Default
    private boolean latestPublish = false;

    /**
     * 多模态文件对象透传
     */
    private List<Object> files;

    /**
     * 多模态文件urls列表
     */
    private List<String> fileUrls;

    /**
     * 统计输入输出文本
     */
    private ModelApiLog apiLog;

    /**
     * 是否老会话
     */
    private boolean oldConversation;

    /**
     * Agent归属的项目ID
     */
    private String ownerProjectId;

    /**
     * Agent归属的空间ID
     */
    private String ownerWorkspaceId;

    private String ownerDomainId;

    private String environmentId;

    /**
     * 是否为网页发布调用
     */
    @Builder.Default
    private boolean isWebPage = false;

    private AgentExecutionInfo executionInfo;

    private ControllerExecutionDetailModel controllerExecution;

    /**
     * IR类型
     */
    private AgentIrType irType;

    /**
     * 消息缓存计数器
     */
    @Builder.Default
    private AtomicInteger messageChunkCount = new AtomicInteger(0);
}

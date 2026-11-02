/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.service.builder;

import com.alibaba.fastjson.JSON;
import com.alibaba.ttl.threadpool.TtlExecutors;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.openjiuwen.studio.agent.space.api.vo.AgentType;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderDispatchVo;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderFileExtConfigVo;
import com.openjiuwen.studio.agent.space.api.vo.request.ChatTemplateRequest;
import com.openjiuwen.studio.agent.space.api.vo.request.AgentBuilderChatReq;
import com.openjiuwen.studio.agent.space.app.constant.Constant;
import com.openjiuwen.studio.agent.space.app.constant.RedisKeyConstant;
import com.openjiuwen.studio.agent.space.app.enums.DRTaskStatusType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderMsgType;
import com.openjiuwen.studio.agent.space.app.service.dispatch.DispatchService;
import com.openjiuwen.studio.agent.space.app.task.DRTaskHandler;
import com.openjiuwen.studio.agent.space.app.util.AppCommonUtils;
import com.openjiuwen.studio.agent.space.app.util.FileTransferUtils;
import com.openjiuwen.studio.agent.space.app.util.MessageFileUtils;
import com.openjiuwen.studio.agent.space.common.context.AuthorizationContextHolder;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.redis.RedisClient;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderFileMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderMessageMapper;
import com.openjiuwen.studio.agent.space.dao.application.AgentBuilderTaskMapper;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderFileEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderMessageEntity;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderTaskEntity;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.Nullable;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.sql.Timestamp;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Execute Service
 */
@Slf4j
@Service
public class AgentBuilderHelperService {
    private static final int HEARTBEAT_INTERVAL_COUNT = 5;

    @Resource
    private AgentBuilderTaskMapper taskMapper;

    @Resource
    private AgentBuilderMessageMapper messageMapper;

    @Resource
    private ScheduledExecutorService scheduledExecutor;

    @Resource
    private RedisClient redisClient;

    @Resource
    private DispatchService dispatchService;

    @Resource
    private MessageFileUtils messageFileUtils;

    @Resource
    private AgentBuilderFileMapper AgentBuilderFileMapper;

    @Resource
    private FileTransferUtils fileTransferUtil;

    @Resource
    private DRTaskHandler drTaskHandler;

    @Value("${agent.builder.task.runtimeQuota.concurrentInstanceNub:200}")
    private int concurrentInstanceNub;

    @Value("${agent.builder.task.runtimeQuota.concurrentInstanceNub4User:2}")
    private int concurrentInstanceNub4User;

    @Value("#{'${agent.builder.task.whiteList.concurrencyControl4User:087708f382d2471bbd4649a97346530d}'.split(',')}")
    private List<String> concurrencyControl4UseWhiteList;

    @Value("${agent.space.chat.bucketName:agentBuilder}")
    private String normalAgentBucketName;

    @Value("${agent.space.downloadurl.expires:7}")
    private long downloadUrlExpires;

    /**
     * 执行聊天任务并保存消息
     *
     * @param req  调用运行时接口的参数
     * @param task agent的运行时地址
     */
    @Transactional
    protected boolean saveAndExecuteChat(AgentBuilderChatReq req, AgentBuilderTaskEntity task, String workspaceId) {
        String lock = String.format(RedisKeyConstant.DR_SSE_LOCK, req.getTaskId());
        boolean locked = redisClient.tryLockWithId(lock, req.getTaskId(), 60 * 120);
        if (Boolean.FALSE.equals(locked)) {
            // 没拿到锁，说明已经有异步任务建立了SSE连接，不能重复建立，只做流式数据返回
            log.warn("[saveAndExecuteChat] get lock failed!");
            return true;
        }
        try {
            // 先清理已有的消息，中断前的消息会从list/message获取
            String chunksKey = String.format(RedisKeyConstant.DR_CHUNKS, req.getTaskId());
            redisClient.deleteKeys(Set.of(chunksKey));
            // message 落库
            AgentBuilderMessageEntity query = new AgentBuilderMessageEntity().setId(AppCommonUtils.getUUID())
                .setTaskId(task.getId())
                .setType(AgentBuilderMsgType.USER.getType())
                .setContent(req.getQuery())
                .setFileList(CollectionUtils.isEmpty(req.getFiles()) ? new ArrayList<>() : req.getFiles())
                .setRating(-1);
            AppCommonUtils.setCommonCreateProperties(query);
            query.setCreatedDate(new Timestamp(System.currentTimeMillis()));
            AgentBuilderMessageEntity answer = new AgentBuilderMessageEntity().setId(AppCommonUtils.getUUID())
                .setParentId(query.getId())
                .setTaskId(task.getId())
                .setType(AgentBuilderMsgType.SYSTEM.getType())
                .setContent("")
                .setFileList(new ArrayList<>())
                .setRating(-1);
            AppCommonUtils.setCommonCreateProperties(answer);
            answer.setCreatedDate(new Timestamp(System.currentTimeMillis() + 1));
            messageMapper.insertBatchSomeColumn(List.of(query, answer));

            String templatePathKey = String.format(RedisKeyConstant.DR_TEMPLATE, task.getId());
            ChatTemplateRequest chatTemplateRequest = getTemplateRequest(req, task, query.getId(), templatePathKey);

            // 组装调度服务所需数据
            AgentBuilderDispatchVo dispatchInfo = new AgentBuilderDispatchVo().setTaskId(task.getId())
                .setAnswerId(answer.getId())
                .setQuery(req.getQuery())
                .setInputs(req.getInputs().setTemplate(chatTemplateRequest))
                .setFiles(req.getFiles())
                .setRunType(task.getRunType())
                .setAgentId(task.getAgentId())
                .setTaskStatus(task.getStatus())
                .setWorkspaceId(workspaceId)
                .setStartTime(answer.getCreatedDate());

            AppCommonUtils.setCommonUpdateProperties(task);

            // 更新任务修改人和修改时间，任务状态由dispatchTask函数中的逻辑更新
            LambdaUpdateWrapper<AgentBuilderTaskEntity> taskUpdateWrapper
                = new LambdaUpdateWrapper<AgentBuilderTaskEntity>().set(AgentBuilderTaskEntity::getLastUpdatedDate,
                    task.getLastUpdatedDate())
                .set(AgentBuilderTaskEntity::getLastUpdatedByUserId, task.getLastUpdatedByUserId())
                .eq(AgentBuilderTaskEntity::getId, task.getId());
            taskMapper.update(taskUpdateWrapper);

            dispatchService.dispatchTask(dispatchInfo);
        } catch (Exception e) {
            log.error("[saveAndExecuteChat] save task err", e);
            drTaskHandler.updateTaskStatus(req.getTaskId(), DRTaskStatusType.FAIL.getStatus());
            // 异常时释放锁，正常拉起SSE连接后在异步任务中管理锁
            redisClient.unlockWithId(lock, req.getTaskId());
            log.info("taskId:{} release lock success.", req.getTaskId());
            return false;
        }
        return true;
    }

    private @Nullable ChatTemplateRequest getTemplateRequest(AgentBuilderChatReq req, AgentBuilderTaskEntity task,
        String messageId, String templatePathKey) {
        String templateFileId = StringUtils.EMPTY;
        if (task.getStatus() == DRTaskStatusType.INITIATING.getStatus() && ObjectUtils.isNotEmpty(req.getFiles())) {
            // 校验文件，把文件从临时目录copy到正式目录，并把临时目录中的文件删除
            templateFileId = messageFileUtils.tempFileBindTask(task, List.of(req.getFiles().get(0))).get(0);
        }
        ChatTemplateRequest chatTemplateRequest = null;
        if (!templateFileId.isEmpty()) {
            AgentBuilderFileEntity fileEntity = AgentBuilderFileMapper.selectById(templateFileId);
            AgentBuilderFileMapper.updateMessageId(List.of(fileEntity.getId()), messageId);
            String templatePath = fileTransferUtil.getDownloadUrlFromObs(normalAgentBucketName, fileEntity.getUri(),
                downloadUrlExpires);
            AgentBuilderFileExtConfigVo extConfigVo = JSON.parseObject(fileEntity.getExtraConfig(),
                AgentBuilderFileExtConfigVo.class);
            chatTemplateRequest = new ChatTemplateRequest().setIsTemplate(extConfigVo.isTemplate())
                .setFileName(fileEntity.getName())
                .setFilePath(templatePath);
            redisClient.set(templatePathKey, JSON.toJSONString(chatTemplateRequest),
                Duration.ofSeconds(Constant.REDIS_EXPIRE_TIME));
        }
        if (chatTemplateRequest == null) {
            String templateInfo = redisClient.get(templatePathKey);
            if (templateInfo != null && !templateInfo.isEmpty()) {
                chatTemplateRequest = JSON.parseObject(templateInfo, ChatTemplateRequest.class);
            }
        }
        return chatTemplateRequest;
    }

    /**
     * 校验是否超总并发
     */
    protected void checkConcurrencyOfTotal() {
        Long runningCount = taskMapper.selectCount(
            new LambdaQueryWrapper<AgentBuilderTaskEntity>().eq(AgentBuilderTaskEntity::getAgentType,
                    AgentType.DEEP_RESEARCH.getCode())
                .eq(AgentBuilderTaskEntity::getDeleted, false)
                .in(AgentBuilderTaskEntity::getStatus, DRTaskStatusType.getRunningStatus()));
        if (runningCount > concurrentInstanceNub) {
            log.error("[createTask] validate task fail, running task count exceed limit, tenantId: {}, limit: {},"
                + " current: {}", AuthorizationContextHolder.domainId(), concurrentInstanceNub, runningCount);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_RUNNING_TASK_EXCEED_LIMIT_ERROR);
        }
    }

    /**
     * 校验是否超用户并发
     */
    protected void checkConcurrencyOfUser() {
        if (!concurrencyControl4UseWhiteList.contains(AuthorizationContextHolder.domainId())) {
            // 用户并发控制，在生命周期内的任务最多只能有两个
            LambdaQueryWrapper<AgentBuilderTaskEntity> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(AgentBuilderTaskEntity::getAgentType, AgentType.DEEP_RESEARCH.getCode())
                .eq(AgentBuilderTaskEntity::getDeleted, false)
                .eq(AgentBuilderTaskEntity::getDomainId, AuthorizationContextHolder.domainId())
                .eq(AgentBuilderTaskEntity::getCreatedByUserId, AuthorizationContextHolder.userId())
                .in(AgentBuilderTaskEntity::getStatus, DRTaskStatusType.getRunningStatus());
            Long currentRunningTaskCount = taskMapper.selectCount(queryWrapper);
            if (currentRunningTaskCount >= concurrentInstanceNub4User) {
                log.error("[createTask] validate task fail, running task count for user exceed limit, tenantId: {},"
                        + " userId: {}, limit: {}, current: {}", AuthorizationContextHolder.domainId(),
                    AuthorizationContextHolder.userId(), concurrentInstanceNub4User, currentRunningTaskCount);
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_RUNNING_TASK_EXCEED_LIMIT_FOR_USER_ERROR,
                    AuthorizationContextHolder.userId(), concurrentInstanceNub4User, currentRunningTaskCount);
            }
        }
    }

    protected SseEmitter getSseEmitter(AgentBuilderChatReq req) {
        String taskId = req.getTaskId();
        SseEmitter emitter = new SseEmitter(120 * 60 * 1000L);
        String chunksKey = String.format(RedisKeyConstant.DR_CHUNKS, taskId);
        String statusKey = String.format(RedisKeyConstant.DR_STATUS, taskId);
        AtomicInteger lastIndex = new AtomicInteger();

        ScheduledExecutorService executorService = TtlExecutors.getTtlScheduledExecutorService(scheduledExecutor);
        // 先设置 AtomicReference 占位，避免定时任务执行时出现 NullPointerException
        AtomicReference<ScheduledFuture<?>> pollingTaskRef = new AtomicReference<>();
        // 计数器，每5次轮询即10s发送一次心跳。
        final AtomicInteger pollCounter = new AtomicInteger(0);
        // 创建 Callable 包装器，以便处理任务创建异常
        ScheduledFuture<?> pollingTask = executorService.scheduleAtFixedRate(() -> {
            boolean hasSentData = false; // 记录本轮是否发送了数据
            try {
                String status = redisClient.get(statusKey);
                Long listLen = redisClient.lSize(chunksKey);
                int currentLastIndex = listLen == null ? -1 : listLen.intValue() - 1;

                log.info("[SSE] Current status: {}, current last index: {}", status, currentLastIndex);

                if (currentLastIndex >= lastIndex.get()) {
                    List<String> newChunks = redisClient.lRange(chunksKey, lastIndex.get(), currentLastIndex);
                    if (newChunks != null && !newChunks.isEmpty()) {
                        int newChunksSize = newChunks.size();
                        log.info("[SSE] Found {} new chunks to send: {}", newChunksSize, newChunks);

                        for (String chunk : newChunks) {
                            emitter.send(chunk);
                        }
                        lastIndex.set(lastIndex.get() + newChunksSize);
                        hasSentData = true;
                        // 发送了数据后，重置计数器
                        pollCounter.set(0);
                        log.info("[SSE] task {} pushed {} new chunks, current last index: {}", taskId, newChunksSize,
                            lastIndex.get());
                    }
                } else {
                    if (status != null && !DRTaskStatusType.isRunning(
                        DRTaskStatusType.getByStatus(Integer.parseInt(status)))) {
                        log.info("[SSE] Agent status for task {} is completed, completing SSE connection", taskId);
                        emitter.send("{\"event\":\"done\"}");
                        emitter.complete();
                        // 从 AtomicReference 获取并终止任务（此时已初始化）
                        ScheduledFuture<?> task = pollingTaskRef.get();
                        if (task != null) {
                            task.cancel(false);
                        }
                        return;
                    }
                }
                if (!hasSentData) {
                    int count = pollCounter.incrementAndGet();
                    if (count >= HEARTBEAT_INTERVAL_COUNT) {
                        // 发送心跳，虽然SSE已经设置了长连接，但是防止网关或者elb那边长时间不接受数据会关闭连接，因此发送一个心跳，防止断开连接
                        emitter.send("heartbeat");
                        log.info("[SSE] Heartbeat sent ({}s interval)", HEARTBEAT_INTERVAL_COUNT * 2);
                        // 重置计数器
                        pollCounter.set(0);
                    }
                }
            } catch (Exception e) {
                log.error("[SSE] Failed to poll new data for task {}", taskId);
                emitter.completeWithError(e);
                // 异常时终止任务
                ScheduledFuture<?> task = pollingTaskRef.get();
                if (task != null) {
                    task.cancel(false);
                }
            }
        }, 2000, 2000, TimeUnit.MILLISECONDS);

        // 将任务引用存入 AtomicReference
        pollingTaskRef.set(pollingTask);

        // 监听 SSE 连接关闭，终止轮询任务
        emitter.onCompletion(() -> {
            log.info("[SSE] SSE connection completed for task {}, terminating polling task", taskId);
            onSseClose(emitter, pollingTaskRef, taskId);
        });
        emitter.onError((e) -> {
            log.error("[SSE] SSE connection error for task {}, terminating polling task, error: {}", taskId,
                e.getMessage());
            onSseClose(emitter, pollingTaskRef, taskId);
        });
        emitter.onTimeout(() -> {
            log.warn("[SSE] SSE connection timeout for task {}, terminating polling task", taskId);
            onSseClose(emitter, pollingTaskRef, taskId);
        });

        return emitter;
    }

    private void onSseClose(SseEmitter emitter, AtomicReference<ScheduledFuture<?>> pollingTaskRef, String taskId) {
        ScheduledFuture<?> task = pollingTaskRef.get();
        if (task != null) {
            task.cancel(false);
        }
        try {
            emitter.send("{\"event\":\"done\"}");
        } catch (IOException ignored) {
            log.error("[onSseClose] send done err {}", taskId);
        } finally {
            emitter.complete();
        }
    }
}

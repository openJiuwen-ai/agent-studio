/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static java.time.temporal.ChronoUnit.DAYS;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.redis.RedisReadOverflowException;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.manager.dto.ConversationInfoList;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.manager.dto.ExecutionInfoList;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * 工作流运行实例服务
 *
 */
@Slf4j
@Service
public class WorkflowInstanceService {
    @Autowired
    private RedisClient redisClient;

    @Autowired
    private RedisHistoryEvictionService redisHistoryEvictionService;

    /**
     * 调试记录实时持久化的旁路线程池，避免在 OkHttp SSE 回调线程上同步写 Redis 阻塞事件透传。
     * {@link com.openjiuwen.studio.agent.manager.config.AsyncConfig#insightPersistenceExecutor}
     */
    @Autowired
    @org.springframework.beans.factory.annotation.Qualifier("insightPersistenceExecutor")
    private Executor insightPersistenceExecutor;

    @Value("${workflow.insight-exec-rel:}")
    private String insightExecRel;  // 一个conversation下的execution记录

    @Value("${workflow.insight-conv-rel:}")
    private String insightConvRel; // 一个workflow下的 conversation记录

    @Value("${workflow.insight-exec:}")
    private String insightExec;

    @Value("${workflow.insight-exec-events:}")
    private String insightExecEvents;

    /**
     * 调试记录分 key 存储开关。开启后 meta 与 events 分离存储（避免单 key 全量序列化 O(N²) 读写阻塞）；
     * 关闭时保持原样（单 key 全量序列化）。读取始终兼容两种格式，开关切换不影响已有数据读取。
     */
    @Value("${workflow.insight-multi-key-enabled:false}")
    private boolean insightMultiKeyEnabled;

    /**
     * 调试记录实时旁路写总开关（新增特性，默认关闭）。
     * false=运行中不对每个节点事件写 Redis，{@code saveInsightMessageAsync} 短路为 no-op，
     *      仅终态 {@code saveTerminal} 落盘完整数据；实时调试更新走 SSE 透传，不落库。
     * true=按 {@code insightFlushIntervalMs}/{@code insightFlushMaxSkip} 节流实时旁路写。默认 false。
     */
    @Value("${workflow.insight-bypass-write-enabled:false}")
    private boolean insightBypassWriteEnabled;

    @Value("${workflow.instance-expire:}")
    private Long instExpire;

    @Value("${workflow.conversation-expire:}")
    private Long convExpire;

    @Value("${workflow.max-execution-size:}")
    private Integer maxExecutionSize;

    @Value("${workflow.max-conversation-size:}")
    private Integer maxConversationSize;

    @Value("${workflow.insight-flush-interval-ms:3000}")
    private long insightFlushIntervalMs;

    @Value("${workflow.insight-flush-max-skip:20}")
    private int insightFlushMaxSkip;

    /**
     * 从 events List 读取事件流的单次 LRANGE 批量。
     * 分批滚动拉取，避免单次 {@code lRange(0, -1)} 全量拉取大 List 阻塞 Redis 单线程、
     * 触发 Redisson 响应超时重试（历史故障：9 秒空等后异常被吞、返回空 event_list）。
     * 单批 KB 级，Redis 端耗时 <5ms，不进 slowlog、不排队、不超时。默认 200。
     */
    @Value("${workflow.insight-events-load-batch:200}")
    private int insightEventsLoadBatch;

    /**
     * 按会话(executionId)维度的旁路写节流状态。
     * 每个 WORKFLOW_NODE_MESSAGE 事件都触发 saveInsightMessageAsync，但只有
     * 距上次写入超过 insightFlushIntervalMs 或累计跳过超过 insightFlushMaxSkip 次时才真正提交异步写。
     * 被跳过的事件不丢失：eventList 在内存持续累积，终态 saveInstance 会兜底写入完整数据。
     *
     * <p>用 Caffeine {@link Cache} 而非 ConcurrentHashMap，{@code expireAfterAccess} 兜底回收：
     * 正常流终态 {@link #saveTerminal} / {@link #deleteExecution} 会显式 invalidate 及时清理；
     * 若终态路径未走到（进程崩溃、异常中断未保存等），10 分钟无访问后自动回收，避免内存泄漏。
     */
    private final Cache<String, FlushState> flushStates = Caffeine.newBuilder()
        .expireAfterAccess(10, TimeUnit.MINUTES)
        .build();

    private static class FlushState {
        final AtomicInteger skipCount = new AtomicInteger(0);
        final AtomicLong lastFlushTime = new AtomicLong(0);
        /**
         * 已提交但尚未完成的旁路异步写。终态保存前 await 全部，避免旧快照在终态之后覆盖。
         * 用队列而非单个 future：多线程池下更早提交的旧快照可能晚于新快照完成，
         * 只 await 最新一个会漏掉旧的。
         */
        final java.util.concurrent.ConcurrentLinkedQueue<CompletableFuture<Void>> pendingWrites =
            new java.util.concurrent.ConcurrentLinkedQueue<>();
    }

    /**
     * 获取工作流运行实例
     *
     * @param workflowInstanceId 工作流运行实例id
     * @return 返回工作流运行实例
     */
    public WorkflowInstanceEntity get(String workflowInstanceId, String versionId) {
        return get(workflowInstanceId, versionId, RequestContextUtils.getRequestUserId());
    }

    public WorkflowInstanceEntity get(String workflowInstanceId, String versionId, String userId) {
        String insightExecKey = getInsightExec(userId, workflowInstanceId, versionId);

        try {
            String instStr = redisClient.get(insightExecKey);
            if (StringUtils.isEmpty(instStr)) {
                return null;
            }
            WorkflowInstanceEntity entity = JSONObject.parseObject(instStr, WorkflowInstanceEntity.class);
            // 新格式：meta 与 events 分离存储，eventCount 非空标记新格式 → 从 events List 合并 eventList
            if (entity != null && entity.getEventCount() != null) {
                entity.setEventList(loadExecutionEvents(userId, workflowInstanceId, versionId));
            }
            // 老格式：eventList 内联在 metaStr 中，直接使用（兼容存量数据）
            return entity;
        } catch (RedisReadOverflowException e) {
            log.warn("Redis read overflow, triggering history eviction for key: {}", e.getRedisKey());
            String cleanedJson = redisHistoryEvictionService.handleReadOverflow(e.getRedisKey());
            if (StringUtils.isNotEmpty(cleanedJson)) {
                WorkflowInstanceEntity entity = JSONObject.parseObject(cleanedJson, WorkflowInstanceEntity.class);
                if (entity != null && entity.getEventCount() != null) {
                    entity.setEventList(loadExecutionEvents(userId, workflowInstanceId, versionId));
                }
                return entity;
            }
            return null;
        } catch (Exception e) {
            log.error("parse workflow instance error", e);
        }
        return null;
    }

    /**
     * 获取工作流运行实例缓存
     *
     * @param workflowInstanceId 工作流运行实例id
     * @param versionId 发布版本号
     * @return 返回工作流运行实例
     */
    public WorkflowInstanceEntity getCache(String workflowInstanceId, String versionId) {
        return get(workflowInstanceId, versionId);
    }

    public WorkflowInstanceEntity getCache(String workflowInstanceId, String versionId, String userId) {
        return get(workflowInstanceId, versionId, userId);
    }

    /**
     * 保存工作流运行实例
     *
     * @param workflowInstanceEntity 工作流运行实例
     */
    public void save(WorkflowInstanceEntity workflowInstanceEntity, ExecuteParams executeParams) {
        if (StringUtils.isEmpty(workflowInstanceEntity.getId())) {
            // id为空，不保存
            log.warn("workflow instance id is null!");
            return;
        }
        String versionId = executeParams.getReleasedVersion();
        String userId = executeParams.getUserId();

        if (executeParams.isDebug()) {
            saveInsightMessage(workflowInstanceEntity, versionId, userId,
                executeParams.getAsyncTaskParamHolder() != null && executeParams.getAsyncTaskParamHolder().isAsync());
        } else if (executeParams.isTrace()) {
            // 非debug模式只保留需上报ops的事件
            List<JiuwenEvent> eventList = workflowInstanceEntity.getEventList()
                .stream()
                .filter(this::getFinishWorkflowNode)
                .collect(Collectors.toList());
            workflowInstanceEntity.setEventList(eventList);
            saveExecution(workflowInstanceEntity, versionId, userId, Duration.ofMinutes(10));
        }
    }

    /**
     * 终态保存（工作流结束）：先等待已提交的旁路异步写完成（顺序屏障，避免旧快照在终态写之后覆盖），
     * 再保存实例（分 key 模式写 meta+索引，原样模式写单 key 全量），分 key 模式开启且为 debug 时再全量落盘 events List。
     * 仅在 WorkflowListener.saveInstance() 终态路径调用。
     */
    public void saveTerminal(WorkflowInstanceEntity workflowInstanceEntity, ExecuteParams executeParams) {
        String execId = workflowInstanceEntity.getId();
        try {
            // 屏障：等待该 executionId 下全部已提交的旁路异步写完成，防止旧快照在终态写之后覆盖。
            // 用 allOf 而非单个 future：多线程池下旧快照可能晚于新快照完成，只 await 最新会漏。
            // 超时兜底（5s）：DiscardPolicy 静默丢弃时 future 靠 orTimeout 自动完成，不无限阻塞。
            if (execId != null) {
                FlushState state = flushStates.getIfPresent(execId);
                if (state != null && !state.pendingWrites.isEmpty()) {
                    CompletableFuture<?>[] futures = state.pendingWrites.toArray(new CompletableFuture[0]);
                    try {
                        CompletableFuture.allOf(futures).get(5, TimeUnit.SECONDS);
                    } catch (Exception e) {
                        log.warn("Wait for in-flight bypass writes timed out, executionId={}. Terminal save proceeds. {}",
                            execId, e.getMessage());
                    }
                }
            }
            save(workflowInstanceEntity, executeParams);
            if (insightMultiKeyEnabled && executeParams.isDebug()) {
                saveExecutionEvents(workflowInstanceEntity, executeParams.getReleasedVersion(),
                    executeParams.getUserId());
            }
        } finally {
            // 终态清理节流状态：invalidate 后新的 saveInsightMessageAsync 会用新 FlushState，
            // 不再有 pendingWrites 指向旧的 inflight future。
            if (execId != null) {
                flushStates.invalidate(execId);
            }
        }
    }

    private boolean getFinishWorkflowNode(JiuwenEvent jiuwenEvent) {
        if (!Strings.CI.equals(jiuwenEvent.getEvent(),
            JiuwenEventType.WORKFLOW_NODE_MESSAGE.name().toLowerCase(Locale.ROOT))) {
            return false;
        }
        JiuwenEventData jiuwenEventData = jiuwenEvent.getData();
        return Strings.CI.equals("finish", jiuwenEventData.getStatus().toString());
    }

    /**
     * 开发存储insight事件接口，异步模式下实时存储
     *
     * @param workflowInstanceEntity 工作流运行实例
     * @param versionId 发布版本号
     * @param userId 用户ID
     */
    public void saveInsightMessage(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId,
        boolean isAsync) {
        // error 日志信息屏蔽jiuwen
        if (StringUtils.isNotBlank(workflowInstanceEntity.getErrorInfo())) {
            workflowInstanceEntity.setErrorInfo(workflowInstanceEntity.getErrorInfo().replaceAll("(?i)(九问|jiuwen)", "Runtime"));
        }
        if (insightMultiKeyEnabled) {
            // 分 key：只写 meta（小对象，不含 eventList），events 由终态全量落盘
            saveExecutionMeta(workflowInstanceEntity, versionId, userId);
        } else {
            // 原样：单 key 全量序列化（含 eventList）
            saveExecution(workflowInstanceEntity, versionId, userId);
        }
        saveExecutionInfos(workflowInstanceEntity, versionId, userId);
        if (!isAsync) {
            saveConversationInfos(workflowInstanceEntity, versionId, userId);
        }
    }

    /**
     * 异步保存调试记录（insight），用于工作流流式执行过程中的实时旁路写。
     *
     * <p>调用方（OkHttp SSE 回调线程）仅负责在当前线程上构造一份快照实体，随后将真正的
     * Redis 写入（序列化 + 分布式锁 + 读改写）丢给 {@link #insightPersistenceExecutor} 执行，
     * 确保 runtime→前端的 {@code passThrough} 事件透传不被 Redis 持久化阻塞。
     *
     * <p>快照在调用线程同步构造：标量字段浅拷贝、{@code eventList} 复制成新 ArrayList。
     * 原因是 {@code eventList} 会被 {@code JiuwenEventProcessor.recordEvent} 在后续事件上并发追加，
     * 若异步序列化时仍读原 list 会触发 {@link java.util.ConcurrentModificationException}。
     * 单个事件对象在记录后不再修改，故 list 元素引用浅拷贝即可。
     *
     * <p>异常全部在异步任务内吞掉并 warn：调试记录是尽力而为的旁路写，
     * 实时快照丢失不影响 {@code saveInstance()} 的终态保存。
     *
     * @param workflowInstanceEntity 工作流运行实例
     * @param versionId 发布版本号
     * @param userId 用户ID
     */
    public void saveInsightMessageAsync(WorkflowInstanceEntity workflowInstanceEntity, String versionId,
        String userId, boolean isAsync) {
        String execId = workflowInstanceEntity.getId();
        if (execId == null) {
            return;
        }
        // 旁路写总开关：关闭时回退到原有同步 saveInsightMessage，保持存量行为不变（逐节点实时落库）。
        // 开启时走节流异步旁路写，避免 Redis 写入阻塞 SSE 事件透传。
        if (!insightBypassWriteEnabled) {
            saveInsightMessage(workflowInstanceEntity, versionId, userId, isAsync);
            return;
        }
        // 节流：按 executionId 维度，只在时间窗口或计数兜底触发时才提交异步写。
        // 被跳过的事件不丢失——eventList 在内存持续累积，终态 saveInstance 会兜底写入完整数据。
        FlushState state = flushStates.get(execId, k -> new FlushState());
        long now = System.currentTimeMillis();
        long last = state.lastFlushTime.get();
        int skipped = state.skipCount.incrementAndGet();
        boolean timeUp = (now - last) >= insightFlushIntervalMs;
        boolean countUp = skipped >= insightFlushMaxSkip;
        if (!timeUp && !countUp) {
            return;
        }
        // 命中写入条件，重置计数器
        state.skipCount.set(0);
        state.lastFlushTime.set(now);

        // 分 key：meta 快照（O(1)，不拷贝 eventList）；原样：整表快照（拷贝 eventList 副本，防并发修改）
        WorkflowInstanceEntity snapshot = insightMultiKeyEnabled
            ? snapshotMeta(workflowInstanceEntity) : snapshotInstance(workflowInstanceEntity);
        String requestId = org.slf4j.MDC.get("request-id");
        // 注册 in-flight future，终态 saveTerminal 会 await 全部，防止旧快照在终态之后覆盖
        CompletableFuture<Void> inflight = new CompletableFuture<>();
        // orTimeout 自完成：DiscardPolicy 静默丢弃时不走 catch、finally 不执行，
        // future 靠 5s 超时自动 complete，避免 saveTerminal 的 allOf 无限等待。
        inflight.orTimeout(5, TimeUnit.SECONDS);
        state.pendingWrites.add(inflight);
        try {
            CompletableFuture.runAsync(
                () -> {
                    if (requestId != null) {
                        org.slf4j.MDC.put("request-id", requestId);
                    }
                    try {
                        saveInsightMessage(snapshot, versionId, userId, isAsync);
                    } catch (Throwable e) {
                        log.warn("Async save insight message failed, executionId={}. {}",
                            snapshot.getId(), e.getMessage(), e);
                    } finally {
                        if (requestId != null) {
                            org.slf4j.MDC.clear();
                        }
                        inflight.complete(null);
                    }
                },
                insightPersistenceExecutor);
        } catch (Throwable e) {
            // RejectedExecutionException（AbortPolicy）走这里；DiscardPolicy 不抛异常、不走这里
            inflight.complete(null);
            log.warn("Submit insight async save rejected, executionId={}. {}", workflowInstanceEntity.getId(),
                e.getMessage());
        }
    }

    /**
     * 构造工作流实例的整表快照（含 eventList 副本），供原样（单 key）模式异步持久化使用，
     * 避免与 SSE 回调线程并发修改 eventList 触发 ConcurrentModificationException。
     */
    private WorkflowInstanceEntity snapshotInstance(WorkflowInstanceEntity source) {
        if (source == null) {
            return null;
        }
        WorkflowInstanceEntity snapshot = new WorkflowInstanceEntity();
        snapshot.setId(source.getId());
        snapshot.setExternalId(source.getExternalId());
        snapshot.setUserId(source.getUserId());
        snapshot.setConversationId(source.getConversationId());
        snapshot.setWorkflowId(source.getWorkflowId());
        snapshot.setProjectId(source.getProjectId());
        snapshot.setInputs(source.getInputs());
        snapshot.setOutputs(source.getOutputs());
        snapshot.setStatus(source.getStatus());
        snapshot.setRunInfo(source.getRunInfo());
        snapshot.setStartTime(source.getStartTime());
        snapshot.setEndTime(source.getEndTime());
        snapshot.setErrorInfo(source.getErrorInfo());
        List<JiuwenEvent> events = source.getEventList();
        snapshot.setEventList(events == null ? null : new ArrayList<>(events));
        return snapshot;
    }

    private void saveExecution(@NotNull WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId) {
        saveExecution(workflowInstanceEntity, versionId, userId, Duration.of(instExpire, DAYS));
    }

    private void saveExecution(@NotNull WorkflowInstanceEntity workflowInstanceEntity, String versionId,
        String userId, Duration ttlDuration) {
        String insightExecKey = getInsightExec(userId, workflowInstanceEntity.getId(), versionId);
        // 事件在 recordEvent 时已由 JiuwenEventProcessor.messageContentClipping 就地裁剪，
        // 快照的 new ArrayList<>(eventList) 只拷贝引用，裁剪已生效，此处无需重复遍历。
        String json;
        try {
            json = JSON.toJSONString(workflowInstanceEntity, JSONWriter.Feature.LargeObject);
        } catch (OutOfMemoryError e) {
            log.error("serialize workflow instance OOM, fallback to summary. executionId={}, eventListSize={}",
                workflowInstanceEntity.getId(),
                workflowInstanceEntity.getEventList() == null ? 0 : workflowInstanceEntity.getEventList().size(), e);
            WorkflowInstanceEntity summary = new WorkflowInstanceEntity();
            summary.setId(workflowInstanceEntity.getId());
            summary.setConversationId(workflowInstanceEntity.getConversationId());
            summary.setWorkflowId(workflowInstanceEntity.getWorkflowId());
            summary.setProjectId(workflowInstanceEntity.getProjectId());
            summary.setStatus(workflowInstanceEntity.getStatus());
            summary.setStartTime(workflowInstanceEntity.getStartTime());
            summary.setEndTime(workflowInstanceEntity.getEndTime());
            summary.setErrorInfo("serialize OOM, eventList truncated");
            summary.setEventList(new ArrayList<>());
            json = JSON.toJSONString(summary);
        }
        redisClient.set(insightExecKey, json, ttlDuration);
    }

    /**
     * 保存工作流实例的元信息（meta）：只写不含 eventList 的小对象，避免每次旁路写都全量序列化 eventList。
     * eventCount 字段作为"新格式"标记，读取时据此从 events List 合并 eventList。
     */
    private void saveExecutionMeta(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId) {
        saveExecutionMeta(workflowInstanceEntity, versionId, userId, Duration.of(instExpire, DAYS));
    }

    private void saveExecutionMeta(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId,
        Duration ttlDuration) {
        String metaKey = getInsightExec(userId, workflowInstanceEntity.getId(), versionId);
        WorkflowInstanceEntity meta = snapshotMeta(workflowInstanceEntity);
        String json;
        try {
            json = JSON.toJSONString(meta, JSONWriter.Feature.LargeObject);
        } catch (OutOfMemoryError e) {
            log.error("serialize workflow instance meta OOM, fallback to minimal. executionId={}",
                workflowInstanceEntity.getId(), e);
            WorkflowInstanceEntity minimal = new WorkflowInstanceEntity();
            minimal.setId(workflowInstanceEntity.getId());
            minimal.setConversationId(workflowInstanceEntity.getConversationId());
            minimal.setWorkflowId(workflowInstanceEntity.getWorkflowId());
            minimal.setProjectId(workflowInstanceEntity.getProjectId());
            minimal.setStatus(workflowInstanceEntity.getStatus());
            minimal.setStartTime(workflowInstanceEntity.getStartTime());
            minimal.setEndTime(workflowInstanceEntity.getEndTime());
            minimal.setErrorInfo("serialize meta OOM");
            minimal.setEventCount(meta.getEventCount());
            json = JSON.toJSONString(minimal);
        }
        redisClient.set(metaKey, json, ttlDuration);
    }

    /**
     * 终态保存：将完整 eventList 全量写入 events List（覆盖式）。
     * 仅在工作流结束时调用，避免过程中每个事件都全量序列化。
     * 单条事件已由 JiuwenEventProcessor.messageContentClipping 裁剪到 KB 级，逐条 RPUSH 不会触发单 value 溢出。
     */
    public void saveExecutionEvents(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId) {
        String eventsKey = getInsightEvents(userId, workflowInstanceEntity.getId(), versionId);
        List<JiuwenEvent> events = workflowInstanceEntity.getEventList();
        if (events == null || events.isEmpty()) {
            // 无事件也清理可能残留的旧 events key（如同一 conversation 重跑）
            redisClient.delete(eventsKey);
            return;
        }
        List<String> jsonList = new ArrayList<>(events.size());
        for (JiuwenEvent event : events) {
            try {
                jsonList.add(JSON.toJSONString(event, JSONWriter.Feature.LargeObject));
            } catch (OutOfMemoryError e) {
                log.error("serialize single event OOM, skip. executionId={}", workflowInstanceEntity.getId(), e);
            }
        }
        // 覆盖式：先删可能残留的旧数据（如重跑），再全量 RPUSH
        redisClient.delete(eventsKey);
        redisClient.rPushAll(eventsKey, jsonList, Duration.of(instExpire, DAYS));
    }

    /**
     * 从 events List 读取并合并事件流（新格式）。
     *
     * <p>按 {@link #insightEventsLoadBatch} 批量滚动拉取，而非单次 {@code lRange(0, -1)} 全量拉取。
     * 单批 KB 级，Redis 端耗时 <5ms，不进 slowlog、不长时间占用单线程导致排队、不触发 Redisson
     * 响应超时重试。单批读取失败（Redisson 超时被 wrapper 吞掉返回 null）只影响末尾，保留已累积批次，
     * 较原先一次失败返回空 event_list 更鲁棒。
     */
    private List<JiuwenEvent> loadExecutionEvents(String userId, String executionId, String versionId) {
        String eventsKey = getInsightEvents(userId, executionId, versionId);
        List<JiuwenEvent> events = new ArrayList<>();
        int batch = Math.max(1, insightEventsLoadBatch);
        for (int offset = 0; ; offset += batch) {
            List<String> jsonList = redisClient.lRange(eventsKey, offset, offset + batch - 1);
            if (jsonList == null || jsonList.isEmpty()) {
                // null：该批读取异常（Redisson 超时被 wrapper 吞掉）。保留已累积批次，不再继续。
                if (jsonList == null && !events.isEmpty()) {
                    log.warn("Partial load: batch read failed at offset {}, returning {} events already loaded. key={}",
                        offset, events.size(), eventsKey);
                }
                break;
            }
            for (String json : jsonList) {
                try {
                    events.add(JSON.parseObject(json, JiuwenEvent.class));
                } catch (Exception e) {
                    log.warn("Failed to parse event from events list, skip. {}", e.getMessage());
                }
            }
            if (jsonList.size() < batch) {
                break;  // 末页
            }
        }
        return events;
    }

    /**
     * 构造 meta 快照（标量字段浅拷贝，eventList 不拷贝，仅记录 eventCount）。
     * 供旁路异步持久化使用：旁路写只更新 meta + 列表索引，事件流由终态全量落盘。
     */
    private WorkflowInstanceEntity snapshotMeta(WorkflowInstanceEntity source) {
        if (source == null) {
            return null;
        }
        WorkflowInstanceEntity snapshot = new WorkflowInstanceEntity();
        snapshot.setId(source.getId());
        snapshot.setExternalId(source.getExternalId());
        snapshot.setUserId(source.getUserId());
        snapshot.setConversationId(source.getConversationId());
        snapshot.setWorkflowId(source.getWorkflowId());
        snapshot.setProjectId(source.getProjectId());
        snapshot.setInputs(source.getInputs());
        snapshot.setOutputs(source.getOutputs());
        snapshot.setStatus(source.getStatus());
        snapshot.setRunInfo(source.getRunInfo());
        snapshot.setStartTime(source.getStartTime());
        snapshot.setEndTime(source.getEndTime());
        snapshot.setErrorInfo(source.getErrorInfo());
        // eventList 不写入 meta；用 eventCount 标记新格式。
        // 优先沿用 source 已有的 eventCount（幂等：对已快照过的 meta 再快照时不会归零），
        // 仅当 source 是未快照过的原始 entity（eventList 非空、eventCount 为空）时才从 size 计算。
        if (source.getEventCount() != null) {
            snapshot.setEventCount(source.getEventCount());
        } else if (source.getEventList() != null) {
            snapshot.setEventCount((long) source.getEventList().size());
        } else {
            snapshot.setEventCount(0L);
        }
        return snapshot;
    }

    public void deleteExecution(String userId, WorkflowInstanceEntity workflowInstanceEntity, String versionId) {
        String insightExecKey = getInsightExec(userId, workflowInstanceEntity.getId(), versionId);
        redisClient.delete(insightExecKey);
        // 同步删除 events List key
        String insightEventsKey = getInsightEvents(userId, workflowInstanceEntity.getId(), versionId);
        redisClient.delete(insightEventsKey);
        // 同步清理节流状态
        String execId = workflowInstanceEntity.getId();
        if (execId != null) {
            flushStates.invalidate(execId);
        }
    }

    /**
     * 将source对象数据clone到target
     *
     * @param source source对象
     * @param target target对象
     */
    public void copy(WorkflowInstanceEntity source, WorkflowInstanceEntity target) {
        target.setId(source.getId());
        target.setExternalId(source.getExternalId());
        target.setConversationId(source.getConversationId());
        target.setWorkflowId(source.getWorkflowId());
        target.setProjectId(source.getProjectId());
        target.setInputs(source.getInputs());
        target.setOutputs(source.getOutputs());
        target.setStatus(source.getStatus());
        target.setRunInfo(source.getRunInfo());
        target.setStartTime(source.getStartTime());
        target.setEndTime(source.getEndTime());
        target.setErrorInfo(source.getErrorInfo());
        if (source.getEventList() == null) {
            target.setEventList(target.getEventList() == null ? new ArrayList<>() : target.getEventList());
            return;
        }
        if (target.getEventList() != null) {
            // 避免覆盖eventList
            target.getEventList().addAll(0, source.getEventList());
        } else {
            target.setEventList(source.getEventList());
        }
    }

    /**
     * 获取工作流对话记录
     *
     * @param workflowId workflowId
     * @param versionId 发布版本号
     * @return 执行记录
     */
    public ConversationInfoList getConversationInfos(String workflowId, String versionId) {
        try {
            String userId = RequestContextUtils.getRequestUserId();
            String conversationInfoKey = getInsightConvRel(workflowId, userId, versionId);

            ConversationInfoList conversationInfos = new ConversationInfoList();
            if (redisClient.exists(conversationInfoKey)) {
                String text = redisClient.get(conversationInfoKey);
                if (StringUtils.isNotEmpty(text)) {
                    conversationInfos = JSON.parseObject(text, ConversationInfoList.class);
                }
            }
            log.info("retrieve: workflowId={}, userId={}, conversationInfoSize={}", workflowId, userId,
                conversationInfos.size());
            return conversationInfos;
        } catch (RedisReadOverflowException e) {
            log.warn("Redis read overflow in getConversationInfos, triggering eviction for key: {}", e.getRedisKey());
            String cleanedJson = redisHistoryEvictionService.handleReadOverflow(e.getRedisKey());
            if (StringUtils.isNotEmpty(cleanedJson)) {
                return JSON.parseObject(cleanedJson, ConversationInfoList.class);
            }
            return new ConversationInfoList();
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 获取工作流会话执行记录
     *
     * @param workflowId workflowId
     * @param versionId 发布版本号
     * @return 执行记录
     */
    public ExecutionInfoList getExecutionInfos(String workflowId, String conversationId, String versionId) {
        try {
            String userId = RequestContextUtils.getRequestUserId();

            String executionInfoKey = getInsightExecRel(workflowId, RequestContextUtils.getRequestUserId(),
                conversationId, versionId);

            ExecutionInfoList executionInfos = new ExecutionInfoList();
            if (redisClient.exists(executionInfoKey)) {
                String text = redisClient.get(executionInfoKey);
                if (StringUtils.isNotEmpty(text)) {
                    executionInfos = JSON.parseObject(text, ExecutionInfoList.class);
                }
            }
            log.info("retrieve: workflowId={}, userId={}, executionInfoSize={}", workflowId, userId,
                executionInfos.size());
            return executionInfos;
        } catch (RedisReadOverflowException e) {
            log.warn("Redis read overflow in getExecutionInfos, triggering eviction for key: {}", e.getRedisKey());
            String cleanedJson = redisHistoryEvictionService.handleReadOverflow(e.getRedisKey());
            if (StringUtils.isNotEmpty(cleanedJson)) {
                return JSON.parseObject(cleanedJson, ExecutionInfoList.class);
            }
            return new ExecutionInfoList();
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 从实例中提取工作流会话记录并保存
     *
     * @param workflowInstanceEntity workflowInstanceEntity
     * @param versionId 发布版本号
     */
    private void saveExecutionInfos(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId) {
        String executionInfoKey = getInsightExecRel(workflowInstanceEntity.getWorkflowId(),
            userId, workflowInstanceEntity.getConversationId(), versionId);
        ExecutionInfoList originExecutionInfos = new ExecutionInfoList();
        if (redisClient.exists(executionInfoKey)) {
            String text = redisClient.get(executionInfoKey);
            if (StringUtils.isNotEmpty(text)) {
                originExecutionInfos = JSON.parseObject(text, ExecutionInfoList.class);
            }
        }
        // 读取历史信息，过滤当前executionInfos
        List<ExecutionInfo> executionInfos = new ExecutionInfoList();
        for (ExecutionInfo executionInfo : originExecutionInfos) {
            if (!Objects.equals(executionInfo.getExecutionId(), workflowInstanceEntity.getId())) {
                executionInfos.add(executionInfo);
            }
        }
        // 更新最新executionInfos，根据size截断
        executionInfos.add(convertExecutionInfo(workflowInstanceEntity));
        int offset = executionInfos.size() - maxExecutionSize;
        if (offset > 0) {
            clearExecutionRecordsAsync(userId, versionId, executionInfos.subList(0, offset));
        }
        executionInfos =
            CommonUtil.subList(offset, maxExecutionSize, executionInfos);
        // 设置info最后更新时间
        redisClient.set(executionInfoKey, JSON.toJSONString(executionInfos), Duration.of(convExpire, DAYS));
        log.info("update: projectId={}, conversationId={}, executionInfoSize={}", workflowInstanceEntity.getProjectId(),
            workflowInstanceEntity.getConversationId(), executionInfos.size());
    }

    private String getInsightExecRel(String workflowId, String userId, String conversationId, String versionId) {
        String executionInfoKey = String.format(insightExecRel, workflowId, userId, conversationId);
        if (!StringUtils.isEmpty(versionId)) {
            return executionInfoKey + "_" + versionId;
        }
        return executionInfoKey;
    }

    private String getInsightConvRel(String workflowId, String userId, String versionId) {
        String conversationInfoKey = String.format(insightConvRel, workflowId, userId);
        if (!StringUtils.isEmpty(versionId)) {
            log.debug("save conInfo versionId is {}", versionId);
            return conversationInfoKey + "_" + versionId;
        }
        return conversationInfoKey;
    }

    private String getInsightExec(String userId, String executionId, String versionId) {
        String insightExecKey = String.format(insightExec, userId, executionId);
        if (!StringUtils.isEmpty(versionId)) {
            return insightExecKey + "_" + versionId;
        }
        return insightExecKey;
    }

    private String getInsightEvents(String userId, String executionId, String versionId) {
        String insightEventsKey = String.format(insightExecEvents, userId, executionId);
        if (!StringUtils.isEmpty(versionId)) {
            return insightEventsKey + "_" + versionId;
        }
        return insightEventsKey;
    }

    private void clearExecutionRecords(String userId, String versionId, List<ExecutionInfo> needDeleteInfos) {
        if (needDeleteInfos == null || needDeleteInfos.isEmpty()) {
            return;
        }
        for (ExecutionInfo info : needDeleteInfos) {
            log.info("Start to clear workflow execution record. userId:{} version:{} executionId:{}", userId, versionId,
                info.getExecutionId());
            String executionInfoKey = getInsightExec(userId, info.getExecutionId(), versionId);
            redisClient.delete(executionInfoKey);
            // 同步删除 events List key
            String eventsKey = getInsightEvents(userId, info.getExecutionId(), versionId);
            redisClient.delete(eventsKey);
        }
    }

    CompletableFuture<Void> clearExecutionRecordsAsync(String userId, String versionId, List<ExecutionInfo> needDeleteInfos) {
        return CompletableFuture.runAsync(() -> clearExecutionRecords(userId, versionId, needDeleteInfos));
    }

    /**
     * 从实例中提取工作流会话记录并保存
     *
     * @param workflowInstanceEntity workflowInstanceEntity
     * @param versionId 发布版本号
     */
    private void saveConversationInfos(WorkflowInstanceEntity workflowInstanceEntity, String versionId, String userId) {
        RedisLock lock = null;
        String conversationInfoKey = getInsightConvRel(workflowInstanceEntity.getWorkflowId(),
            userId, versionId);

        try {
            lock = redisClient.getLock(conversationInfoKey + "_lock");
            // 获取分布式锁，如果锁不可用，则等待3秒，如果还是无法获取，则抛出异常
            if (lock.tryLock(Duration.ofSeconds(3))) {
                ConversationInfoList originConversationInfos = new ConversationInfoList();
                if (redisClient.exists(conversationInfoKey)) {
                    String text = redisClient.get(conversationInfoKey);
                    if (StringUtils.isNotEmpty(text)) {
                        originConversationInfos = JSON.parseObject(text, ConversationInfoList.class);
                    }
                }
                // 读取历史信息，过滤当前conversationInfo
                List<ConversationInfo> conversationInfos = new ConversationInfoList();
                ConversationInfo currentConversationInfo = null;
                for (ConversationInfo conversationInfo : originConversationInfos) {
                    if (!Objects.equals(conversationInfo.getConversationId(),
                        workflowInstanceEntity.getConversationId())) {
                        conversationInfos.add(conversationInfo);
                    } else {
                        currentConversationInfo = conversationInfo;
                    }
                }
                // 如conversation重新执行，更新conversationInfo
                if (currentConversationInfo != null) {
                    currentConversationInfo.setEndTime(workflowInstanceEntity.getEndTime());
                    currentConversationInfo.setOutputs(workflowInstanceEntity.getOutputs());
                    currentConversationInfo.setStatus(workflowInstanceEntity.getStatus());
                } else {
                    currentConversationInfo = convertConversationInfo(workflowInstanceEntity);
                }
                // 更新最新conversationInfos，根据size截断
                conversationInfos.add(currentConversationInfo);

                // 截断超出 maxConversationSize 的旧会话记录（CommonUtil.subList 跳过前 offset 条）。
                // insight_exec_* key 的清理由 saveExecutionInfos 截断 execution 列表时负责，此处无需重复清理。
                int offset = conversationInfos.size() - maxConversationSize;

                conversationInfos = CommonUtil.subList(offset, maxConversationSize, conversationInfos);
                // 设置info最后更新时间
                redisClient.set(conversationInfoKey, JSON.toJSONString(conversationInfos),
                    Duration.of(convExpire, DAYS));
                log.info("update: projectId={}, conversationId={}, workflowId={}, userId={}, conversationInfoSize={}",
                    workflowInstanceEntity.getProjectId(), workflowInstanceEntity.getConversationId(),
                    workflowInstanceEntity.getWorkflowId(), userId,
                    conversationInfos.size());
            } else {
                log.error("failed to get lock, other user is processing same workflow!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * 转换工作流实例为一条执行记录（不包含具体执行信息，仅供列表接口调用）
     *
     * @param workflowInstance workflowInstance
     * @return 执行记录
     */
    public ExecutionInfo convertExecutionInfo(WorkflowInstanceEntity workflowInstance) {
        ExecutionInfo execution = new ExecutionInfo();
        execution.setProjectId(workflowInstance.getProjectId());
        execution.setWorkflowId(workflowInstance.getWorkflowId());
        execution.setConversationId(workflowInstance.getConversationId());
        execution.setExecutionId(workflowInstance.getId());
        execution.setInputs(workflowInstance.getInputs());
        execution.setOutputs(workflowInstance.getOutputs());
        execution.setStatus(workflowInstance.getStatus());
        execution.setErrorInfo(workflowInstance.getErrorInfo());
        execution.setRunInfo(workflowInstance.getRunInfo());
        execution.setStartTime(workflowInstance.getStartTime());
        execution.setEndTime(workflowInstance.getEndTime());
        return execution;
    }

    /**
     * 转换工作流实例为一条conversation记录
     *
     * @param workflowInstance workflowInstance
     * @return 执行记录
     */
    public ConversationInfo convertConversationInfo(WorkflowInstanceEntity workflowInstance) {
        ConversationInfo conversationInfo = new ConversationInfo();
        conversationInfo.setProjectId(workflowInstance.getProjectId());
        conversationInfo.setWorkflowId(workflowInstance.getWorkflowId());
        conversationInfo.setConversationId(workflowInstance.getConversationId());
        conversationInfo.setInputs(workflowInstance.getInputs());
        conversationInfo.setOutputs(workflowInstance.getOutputs());
        conversationInfo.setStatus(workflowInstance.getStatus());
        conversationInfo.setStartTime(workflowInstance.getStartTime());
        conversationInfo.setEndTime(workflowInstance.getEndTime());
        return conversationInfo;
    }
}

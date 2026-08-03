/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.customerheader.AsyncExecutionSnapshot;
import com.openjiuwen.studio.agent.common.customerheader.AsyncIdentitySnapshot;
import com.openjiuwen.studio.agent.common.customerheader.AsyncTaskContextSnapshot;
import com.openjiuwen.studio.agent.common.redis.RedisClient;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * 异步任务上下文快照存储— Redis 单信封
 *
 * <p>单 key {@code agent:runtime:async:context:{taskId}}，一次写入/读取/删除。
 * 旧 key {@code agent:runtime:async:header:{taskId}}（全量 Map）不兼容且不再读取；
 * 升级前排空异步任务，新版本只读新 key；schema 不符 → FAILED 不回退。
 *
 * <p>生命周期：创建任务时 {@link #save}（先于 DB 插入，DB 失败 {@link #delete} 补偿）；
 * 删除任务/过期清理 {@link #delete}；resume 不重写（保持创建者身份）。
 */
@Component
public class AsyncTaskContextSnapshotStore {
    private static final Logger log = LoggerFactory.getLogger(AsyncTaskContextSnapshotStore.class);

    /** 单信封 key（替代旧 async:header:{taskId} 全量 Map） */
    private static final String CONTEXT_KEY_FORMAT = "agent:runtime:async:context:%s";

    /** schema 版本；升级时变更，旧/不符的快照 → load 返回 null → 任务 FAILED 不回退 */
    private static final String SCHEMA_VERSION = "v1";

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private RedisClient redisClient;

    @Value("${task.async.expire-days:7}")
    private int taskAsyncExpireDays;

    /**
     * 保存快照（创建任务时调用，先于 DB 插入）
     *
     * @param taskId    任务 id
     * @param identity   身份快照（平台 Token + effective userId）
     * @param execution  执行快照（客户 header）
     */
    public void save(String taskId, AsyncIdentitySnapshot identity, AsyncExecutionSnapshot execution) {
        try {
            AsyncTaskContextSnapshot snapshot = new AsyncTaskContextSnapshot(SCHEMA_VERSION, identity, execution);
            String json = objectMapper.writeValueAsString(snapshot);
            redisClient.set(String.format(CONTEXT_KEY_FORMAT, taskId), json,
                Duration.ofDays(taskAsyncExpireDays > 0 ? taskAsyncExpireDays : 7));
        } catch (Exception e) {
            log.error("[customer-header] Failed to save async context snapshot for task {}", taskId, e);
            throw new IllegalStateException("Failed to save async context snapshot for task " + taskId, e);
        }
    }

    /**
     * 加载快照（恢复执行时调用）
     *
     * @param taskId 任务 id
     * @return 快照；不存在或 schema 不符返回 null（调用方应置任务 FAILED，不回退）
     */
    public AsyncTaskContextSnapshot load(String taskId) {
        try {
            String json = redisClient.get(String.format(CONTEXT_KEY_FORMAT, taskId));
            if (json == null || json.isEmpty()) {
                return null;
            }
            AsyncTaskContextSnapshot snapshot = objectMapper.readValue(json, AsyncTaskContextSnapshot.class);
            if (snapshot == null || !SCHEMA_VERSION.equals(snapshot.schemaVersion())) {
                log.warn("[customer-header] Async context snapshot schema mismatch for task {}", taskId);
                return null;
            }
            return snapshot;
        } catch (Exception e) {
            log.error("[customer-header] Failed to load async context snapshot for task {}", taskId, e);
            return null;
        }
    }

    /**
     * 删除快照（删任务/过期清理/DB 插入失败补偿时同步调用）
     *
     * @param taskId 任务 id
     */
    public void delete(String taskId) {
        try {
            redisClient.delete(String.format(CONTEXT_KEY_FORMAT, taskId));
        } catch (Exception e) {
            log.warn("[customer-header] Failed to delete async context snapshot for task {}", taskId, e);
        }
    }
}

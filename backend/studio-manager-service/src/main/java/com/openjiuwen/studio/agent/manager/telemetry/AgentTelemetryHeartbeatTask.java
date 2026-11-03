/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.telemetry;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * agent 清单分层心跳任务（漂移令牌门控）。
 *
 * <p>每周期（默认 60s，可配）发送一条聚合轻心跳（在册数 + 漂移令牌），仅当清单发生变化
 * 或到达低频兜底周期时才补发逐 agent 全量快照——安静系统每周期仅 1 条小记录。
 *
 * <p>漂移令牌 = COUNT(*) + MAX(updated_on)（一条 index-only 聚合查询，updated_on 带
 * ON UPDATE CURRENT_TIMESTAMP，任何写操作必然推进）。令牌相对<b>上次成功导出</b>的基线
 * 变化时立即补发全量快照：生命周期事件（edge，精确时间戳）丢失时，≤1 个周期内由全量
 * 快照（level）自愈。导出失败基线不推进，下一周期自动重试。
 *
 * <p>低频兜底（默认 24h，可配、设 0 或负数禁用）：无条件重发一轮全量快照，防接收端自身
 * 丢数据（产出侧不可见的风险）。启动首轮无基线，直接发一轮全量（bootstrap）。
 *
 * <p>多实例部署时通过分布式锁保证同一周期只有一个实例上报。
 */
@Component
@Slf4j
public class AgentTelemetryHeartbeatTask {

    private static final String HEARTBEAT_LOCK = "AGENT_TELEMETRY_HEARTBEAT_LOCK";

    /**
     * 分布式锁等待时间（秒）
     */
    private static final int LOCK_TIME = 10;

    @Autowired
    private AgentTelemetryService telemetryService;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private RedisClient redisClient;

    /**
     * 低频兜底全量快照间隔（毫秒），默认 24h；<=0 表示禁用兜底
     */
    @Value("${studio.agentTelemetry.reconcileIntervalMillis:86400000}")
    private long reconcileIntervalMillis;

    /**
     * 漂移基线：仅在对应全量快照导出成功后推进
     */
    private volatile String confirmedToken;

    private volatile long lastFullSnapshotAt = 0L;

    @Scheduled(fixedDelayString = "${studio.agentTelemetry.heartbeatIntervalMillis:60000}",
        initialDelayString = "${studio.agentTelemetry.heartbeatIntervalMillis:60000}")
    public void emitInventorySnapshot() {
        if (!telemetryService.isEnabled()) {
            return;
        }
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(HEARTBEAT_LOCK);
            if (!lock.tryLock(Duration.ofSeconds(LOCK_TIME))) {
                log.debug("skip agent telemetry heartbeat, another instance holds the lock");
                return;
            }
            Map<String, Object> stat = agentMapper.selectInventoryStat();
            long count = stat.get("agentCount") instanceof Number number ? number.longValue() : 0L;
            String maxUpdatedOn = stat.get("maxUpdatedOn") == null ? "" : String.valueOf(stat.get("maxUpdatedOn"));
            String token = count + ":" + maxUpdatedOn;

            telemetryService.emitHeartbeat(count, maxUpdatedOn);

            boolean drift = confirmedToken == null || !confirmedToken.equals(token);
            boolean reconcileDue = reconcileIntervalMillis > 0
                && System.currentTimeMillis() - lastFullSnapshotAt >= reconcileIntervalMillis;
            if (drift || reconcileDue) {
                telemetryService.emitSnapshot(agentMapper.selectAllActiveAgents(), selectBindingCounts());
                if (telemetryService.flushConfirmed()) {
                    confirmedToken = token;
                    lastFullSnapshotAt = System.currentTimeMillis();
                }
            }
        } catch (Exception e) {
            log.warn("agent telemetry heartbeat failed: {}", e.getMessage());
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * 一次性聚合查询每 agent 的资源绑定数（t_mapping 草稿态，按 app_id + resource_type 分组），
     * 转成 agentId -> resource_type -> 数量；查询失败返回 null，快照退化为不带计数字段。
     */
    private Map<String, Map<String, Long>> selectBindingCounts() {
        try {
            List<Map<String, Object>> rows = agentMapper.selectResourceBindingCounts();
            Map<String, Map<String, Long>> counts = new HashMap<>();
            for (Map<String, Object> row : rows) {
                String agentId = row.get("agentId") == null ? null : String.valueOf(row.get("agentId"));
                String resourceType = row.get("resourceType") == null ? null : String.valueOf(row.get("resourceType"));
                long cnt = row.get("cnt") instanceof Number number ? number.longValue() : 0L;
                if (agentId != null && resourceType != null) {
                    counts.computeIfAbsent(agentId, k -> new HashMap<>()).put(resourceType, cnt);
                }
            }
            return counts;
        } catch (Exception e) {
            log.warn("agent telemetry: binding counts failed: {}", e.getMessage());
            return null;
        }
    }
}

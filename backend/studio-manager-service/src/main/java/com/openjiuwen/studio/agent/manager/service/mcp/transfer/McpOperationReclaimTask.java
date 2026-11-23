/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * FEAT-134 MCP 操作超时回收定时任务。
 *
 * 每 30 秒调用 {@link McpOperationService#reclaimTimedOutOperations()}：
 * 终结超期 RUNNING 操作并把实例上的 active_mcp_operation_id 置空。
 *
 * <p>接线背景：回收方法此前从未被调度（javadoc 声称「每 30 秒由调度器调用」
 * 但无任何调用方），进程重启/任务丢失场景下锁会永久残留（该服务重载/导入
 * 永久 409，无 API 可解锁）。同进程正常完成路径由 submitReload/executeImportItem
 * 的 finally 释放；本任务是崩溃与悬挂场景的唯一兜底。
 *
 * <p>@EnableScheduling 已由 SessionCleanupConfig 开启，此处只需 @Scheduled。
 */
@Component
public class McpOperationReclaimTask {

    private static final Logger log = LoggerFactory.getLogger(McpOperationReclaimTask.class);

    @Autowired
    private McpOperationService operationService;

    /**
     * 每 30 秒回收一次（首次延迟 30 秒，避开启动高峰）。
     */
    @Scheduled(fixedDelay = 30_000L, initialDelay = 30_000L)
    public void reclaimTimedOutOperations() {
        try {
            operationService.reclaimTimedOutOperations();
        } catch (Exception e) {
            // 回收失败不影响下一轮调度（fixedDelay 语义），只记日志
            log.error("mcp operation reclaim task failed", e);
        }
    }
}

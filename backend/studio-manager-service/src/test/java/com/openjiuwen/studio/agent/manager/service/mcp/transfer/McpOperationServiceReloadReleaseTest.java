/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp;
import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentMatchers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * FEAT-134 重载活动操作锁释放回归测试。
 *
 * 背景：重载受理时 claimOperationOnService 声明 active_mcp_operation_id；
 * 成功路径由 commitToolSnapshot 顺带置 NULL，但失败路径曾无任何释放调用——
 * 终态 FAILED 的操作不在超时回收范围（reclaim 只扫 RUNNING 超期），
 * 一次失败会使该服务永久 409 锁死。修复后 submitReload 的 finally 幂等兜底释放。
 */
@DisplayName("McpOperationService.submitReload 失败释放活动操作锁")
@ExtendWith(MockitoExtension.class)
class McpOperationServiceReloadReleaseTest {

    @Mock
    private McpOperationDao operationDao;

    @Mock
    private McpToolSnapshotService snapshotService;

    @Mock
    private ThreadPoolTaskExecutor mcpTaskExecutor;

    @InjectMocks
    private McpOperationService service;

    private McpOperationEntity operation;

    private McpOperationItemEntity item;

    @BeforeEach
    void setUp() {
        // 任务同步执行，便于立即断言 finally 行为
        Mockito.doAnswer(invocation -> {
            ((Runnable) invocation.getArgument(0)).run();
            return null;
        }).when(mcpTaskExecutor).execute(ArgumentMatchers.any(Runnable.class));

        operation = new McpOperationEntity();
        operation.setId("op-1");
        operation.setOperationType(McpTransferOperationResp.TYPE_RELOAD);
        operation.setTenantId("tenant-1");
        operation.setProjectId("proj-1");
        operation.setWorkspaceId("ws-1");
        operation.setStatus(McpTransferOperationResp.STATUS_RUNNING);
        operation.setTotal(1);

        item = new McpOperationItemEntity();
        item.setOperationId("op-1");
        item.setItemIndex(0);
        item.setServiceId("svc-1");
        item.setStatus("PENDING");

        Mockito.when(operationDao.getOperationById("op-1")).thenReturn(operation);
        Mockito.when(operationDao.getOperationItems("op-1")).thenReturn(java.util.List.of(item));

        RequestContextUtils.setContext("token-1", "proj-1", "tenant-1");
    }

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @Test
    @DisplayName("R-01: 执行抛异常终态 FAILED 后必须释放 active_mcp_operation_id")
    void releaseLockWhenExecutionThrows() {
        Mockito.doThrow(new RuntimeException("client failed to initialize"))
            .when(snapshotService).executeReload(operation, item);

        service.submitReload("op-1");

        Mockito.verify(operationDao).releaseOperationOnService("svc-1", "op-1");
    }

    @Test
    @DisplayName("R-02: 正常完成（快照已提交）后 finally 仍幂等释放")
    void releaseLockAfterNormalCompletion() {
        Mockito.doNothing().when(snapshotService).executeReload(operation, item);

        service.submitReload("op-1");

        Mockito.verify(operationDao).releaseOperationOnService("svc-1", "op-1");
    }

    @Test
    @DisplayName("R-03: executeReload 内部 failItem 返回（拉取失败保护原状路径）后同样释放")
    void releaseLockWhenExecuteReloadFailsItem() {
        // 模拟 executeReload 内部失败路径：fetchTools 失败 → failItem 后 return
        Mockito.doAnswer(invocation -> {
            McpOperationItemEntity it = invocation.getArgument(1);
            it.setStatus("FAILED");
            return null;
        }).when(snapshotService).executeReload(operation, item);

        service.submitReload("op-1");

        Mockito.verify(operationDao).releaseOperationOnService("svc-1", "op-1");
    }
}

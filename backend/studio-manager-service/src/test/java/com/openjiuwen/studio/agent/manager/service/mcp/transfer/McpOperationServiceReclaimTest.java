/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp;
import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * FEAT-134 超时回收回归测试。
 *
 * 背景：reclaimTimedOutOperations 曾从未被调度（接线见 McpOperationReclaimTask），
 * 进程重启/任务丢失场景下 active_mcp_operation_id 永久残留、服务重载/导入永久 409。
 * 本测试验证回收逻辑本身：超期 RUNNING 操作的 PENDING 项终结为 FAILED（1188）、
 * 锁释放、操作置 INTERRUPTED；已终态项不重复处理；单项异常不扩散。
 */
@DisplayName("McpOperationService.reclaimTimedOutOperations")
@ExtendWith(MockitoExtension.class)
class McpOperationServiceReclaimTest {

    @Mock
    private McpOperationDao operationDao;

    @InjectMocks
    private McpOperationService service;

    private McpOperationEntity operation;

    private McpOperationItemEntity item;

    @BeforeEach
    void setUp() {
        operation = new McpOperationEntity();
        operation.setId("op-stuck");
        operation.setOperationType(McpTransferOperationResp.TYPE_IMPORT);
        operation.setTenantId("tenant-1");
        operation.setProjectId("proj-1");
        operation.setWorkspaceId("ws-1");
        operation.setStatus(McpTransferOperationResp.STATUS_RUNNING);

        item = new McpOperationItemEntity();
        item.setOperationId("op-stuck");
        item.setItemIndex(0);
        item.setServiceId("svc-1");
        item.setStatus("PENDING");
    }

    @Test
    @DisplayName("R-01: 超期 RUNNING 的 PENDING 项终结 FAILED(1188) 并释放锁")
    void reclaimsPendingItemAndReleasesLock() {
        when(operationDao.getTimedOutRunningOperations(50)).thenReturn(List.of("op-stuck"));
        when(operationDao.getOperationById("op-stuck")).thenReturn(operation);
        when(operationDao.getOperationItems("op-stuck")).thenReturn(List.of(item));

        service.reclaimTimedOutOperations();

        assertEquals("FAILED", item.getStatus());
        assertEquals(StudioError.MCP_OPERATION_INTERRUPTED.getCode(), item.getErrorCode());
        verify(operationDao).finishOperationItem(item);
        verify(operationDao).releaseOperationOnService("svc-1", "op-stuck");
        verify(operationDao).markOperationInterrupted("op-stuck");
    }

    @Test
    @DisplayName("R-02: 已终态项不重复处理（锁仍释放、不覆盖终态）")
    void skipsFinishedItems() {
        item.setStatus("SUCCESS");
        when(operationDao.getTimedOutRunningOperations(50)).thenReturn(List.of("op-stuck"));
        when(operationDao.getOperationById("op-stuck")).thenReturn(operation);
        when(operationDao.getOperationItems("op-stuck")).thenReturn(List.of(item));

        service.reclaimTimedOutOperations();

        // SUCCESS 不被覆盖为 FAILED；锁仍要释放（回收路径本就为清残留）
        assertEquals("SUCCESS", item.getStatus());
        verify(operationDao).releaseOperationOnService("svc-1", "op-stuck");
        verify(operationDao, never()).finishOperationItem(any(McpOperationItemEntity.class));
    }

    @Test
    @DisplayName("R-03: 单项回收异常不影响其余操作（逐操作 try/catch）")
    void perOperationFailureIsolated() {
        when(operationDao.getTimedOutRunningOperations(50)).thenReturn(List.of("op-bad", "op-good"));
        when(operationDao.getOperationById(anyString()))
            .thenThrow(new RuntimeException("db glitch"))
            .thenReturn(operation);
        when(operationDao.getOperationItems("op-good")).thenReturn(List.of(item));

        service.reclaimTimedOutOperations();

        // op-bad 抛错被吞，op-good 照常回收
        assertEquals("FAILED", item.getStatus());
        verify(operationDao).releaseOperationOnService("svc-1", "op-good");
    }

    @Test
    @DisplayName("R-04: 调度任务转发调用且异常不外抛（fixedDelay 语义不被打断）")
    void reclaimTaskDelegatesAndSwallows() throws Exception {
        McpOperationService mockService = Mockito.mock(McpOperationService.class);
        McpOperationReclaimTask task = new McpOperationReclaimTask();
        Field field = McpOperationReclaimTask.class.getDeclaredField("operationService");
        field.setAccessible(true);
        field.set(task, mockService);

        task.reclaimTimedOutOperations();
        verify(mockService).reclaimTimedOutOperations();

        Mockito.doThrow(new RuntimeException("scheduled boom")).when(mockService).reclaimTimedOutOperations();
        assertDoesNotThrow(task::reclaimTimedOutOperations);
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.dto.ExceptionProcess;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.service.IrAdapterService;

import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * McpNodeAdapter 单元测试 — MCP 节点异常处理相关。
 *
 * 覆盖：
 * 1. adaptConfig() — exception_enable/exception_suppression 透传
 * 2. validExceptionProcessParam() — MCP 节点的 timeout(0.1~900) / retryTimes(0~3) 校验
 * 3. getNodeType() — 返回 jiuwen.mcp
 */
class McpNodeAdapterTest {

    private final McpNodeAdapter adapter = new McpNodeAdapter();

    // ─── helpers ────────────────────────────────────────────────────

    private WorkflowNodeVO makeMcpNode(Map<String, Object> configs) {
        WorkflowNodeVO vo = new WorkflowNodeVO();
        vo.setType("Mcp");
        vo.setName("MCP测试节点");
        vo.setConfigs(configs);
        return vo;
    }

    private Map<String, Object> baseMcpConfigs() {
        Map<String, Object> configs = new HashMap<>();
        configs.put("id", "test_mcp_server_id");
        configs.put("name", "test_server_name");
        configs.put("tool_name", "calculate");
        configs.put("streaming", false);
        return configs;
    }

    // ─── getNodeType ────────────────────────────────────────────────

    @Test
    void getNodeType_isMcpIrType() {
        assertEquals(NodeType.MCP.getIrType(), adapter.getNodeType());
    }

    // ─── adaptConfig — exception_enable/exception_suppression 透传 ──

    @Test
    void adaptConfig_copiesExceptionEnableAndSuppression() {
        Map<String, Object> configs = baseMcpConfigs();
        configs.put("exception_enable", true);
        configs.put("exception_suppression", false);
        WorkflowNodeVO vo = makeMcpNode(configs);

        IrAdapterService irAdapterService = Mockito.mock(IrAdapterService.class);
        Map<String, Object> mcpServerConfig = new HashMap<>();
        mcpServerConfig.put("url", "http://localhost:8005/sse");
        mcpServerConfig.put("type", "sse");

        try (MockedStatic<SpringBeanUtils> beans = mockStatic(SpringBeanUtils.class);
             MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            beans.when(() -> SpringBeanUtils.getBean(IrAdapterService.class)).thenReturn(irAdapterService);
            ctx.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("ws-1");
            when(irAdapterService.parseMcpConfigForWorkflow(
                "test_mcp_server_id", "calculate", "proj-1", "user-1", "ws-1"))
                .thenReturn(mcpServerConfig);

            Map<String, Object> result = adapter.adaptConfig(vo);

            assertEquals("http://localhost:8005/sse", result.get("url"));
            // exception_enable → exceptionEnable (camelCase)
            assertEquals(true, result.get("exceptionEnable"));
            // exception_suppression → exceptionSuppression
            assertEquals(false, result.get("exceptionSuppression"));
        }
    }

    @Test
    void adaptConfig_noExceptionConfig_doesNotCopyExceptionFields() {
        Map<String, Object> configs = baseMcpConfigs();
        // 不设置 exception_enable
        WorkflowNodeVO vo = makeMcpNode(configs);

        IrAdapterService irAdapterService = Mockito.mock(IrAdapterService.class);
        Map<String, Object> mcpServerConfig = new HashMap<>();
        mcpServerConfig.put("url", "http://localhost:8005/sse");

        try (MockedStatic<SpringBeanUtils> beans = mockStatic(SpringBeanUtils.class);
             MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            beans.when(() -> SpringBeanUtils.getBean(IrAdapterService.class)).thenReturn(irAdapterService);
            ctx.when(RequestContextUtils::getRequestProjectId).thenReturn("proj-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("ws-1");
            when(irAdapterService.parseMcpConfigForWorkflow(
                Mockito.anyString(), Mockito.anyString(),
                Mockito.anyString(), Mockito.anyString(), Mockito.anyString()))
                .thenReturn(mcpServerConfig);

            Map<String, Object> result = adapter.adaptConfig(vo);

            // exception_enable 未设置 → 不应出现 exceptionEnable
            assertTrue(!result.containsKey("exceptionEnable"));
        }
    }

    // ─── validExceptionProcessParam — MCP 通用校验 ──────────────────

    @Test
    void validExceptionProcessParam_mcpValidConfig_passes() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(300.0)
            .setRetryTimes(2)
            .setHandleType(ExceptionProcess.HandleTypeEnum.ERRORBRANCH);

        // 不应抛异常
        adapter.validExceptionProcessParam(vo, ep);
    }

    @Test
    void validExceptionProcessParam_mcpAllHandleTypes_pass() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        // MCP 支持所有三种 handleType
        for (ExceptionProcess.HandleTypeEnum type : ExceptionProcess.HandleTypeEnum.values()) {
            ExceptionProcess ep = new ExceptionProcess()
                .setTimeout(60.0)
                .setRetryTimes(0)
                .setHandleType(type);
            adapter.validExceptionProcessParam(vo, ep);
        }
    }

    @Test
    void validExceptionProcessParam_mcpTimeoutTooHigh_throws() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(901.0)
            .setRetryTimes(0)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);

        assertThrows(AgentStudioException.class, () -> adapter.validExceptionProcessParam(vo, ep));
    }

    @Test
    void validExceptionProcessParam_mcpTimeoutTooLow_throws() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(0.05)
            .setRetryTimes(0)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);

        assertThrows(AgentStudioException.class, () -> adapter.validExceptionProcessParam(vo, ep));
    }

    @Test
    void validExceptionProcessParam_mcpTimeoutBoundary_passes() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        // 0.1 是合法下限
        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(0.1)
            .setRetryTimes(0)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);
        adapter.validExceptionProcessParam(vo, ep);

        // 900 是合法上限
        ep.setTimeout(900.0);
        adapter.validExceptionProcessParam(vo, ep);
    }

    @Test
    void validExceptionProcessParam_mcpRetryNegative_throws() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(60.0)
            .setRetryTimes(-1)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);

        assertThrows(AgentStudioException.class, () -> adapter.validExceptionProcessParam(vo, ep));
    }

    @Test
    void validExceptionProcessParam_mcpRetryTooHigh_throws() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(60.0)
            .setRetryTimes(4)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);

        assertThrows(AgentStudioException.class, () -> adapter.validExceptionProcessParam(vo, ep));
    }

    @Test
    void validExceptionProcessParam_mcpRetryBoundary_passes() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        // 0 是合法下限
        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(60.0)
            .setRetryTimes(0)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);
        adapter.validExceptionProcessParam(vo, ep);

        // 3 是合法上限
        ep.setRetryTimes(3);
        adapter.validExceptionProcessParam(vo, ep);
    }

    @Test
    void validExceptionProcessParam_mcpNullHandleType_throws() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        ExceptionProcess ep = new ExceptionProcess()
            .setTimeout(60.0)
            .setRetryTimes(0);
        // handleType 未设置 → null

        assertThrows(AgentStudioException.class, () -> adapter.validExceptionProcessParam(vo, ep));
    }

    @Test
    void validExceptionProcessParam_mcpNullTimeout_passes() {
        WorkflowNodeVO vo = makeMcpNode(baseMcpConfigs());

        // timeout 为 null 时不触发范围校验
        ExceptionProcess ep = new ExceptionProcess()
            .setRetryTimes(0)
            .setHandleType(ExceptionProcess.HandleTypeEnum.INTERRUPT);

        adapter.validExceptionProcessParam(vo, ep);
    }
}

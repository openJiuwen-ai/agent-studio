/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import java.util.List;
import java.util.Map;

/**
 * FEAT-134 MCP 工具拉取结果（typed）。
 *
 * 区分「合法空工具列表」与「失败」——旧安装链路把空列表折成空串当失败，
 * 新导入/重载链路消费本类型：success=true 且 tools 为空数组是合法终态。
 */
public record McpToolFetchResult(boolean success, List<Map<String, Object>> tools, String errorCode,
    String safeReason) {

    public static McpToolFetchResult ok(List<Map<String, Object>> tools) {
        return new McpToolFetchResult(true, tools, null, null);
    }

    public static McpToolFetchResult fail(String errorCode, String safeReason) {
        return new McpToolFetchResult(false, List.of(), errorCode, safeReason);
    }
}

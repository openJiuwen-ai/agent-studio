/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

/**
 * FEAT-134 NPX/UVX 目标部署适配器。
 *
 * L2 §5.7 基线缺口：当前代码有 APIG 创建服务类，但 deploy 链路未形成 NPX/UVX
 * 基础设施创建调用。基线适配器明确返回不可用（MCP_DEPLOYMENT_UNAVAILABLE），
 * 不伪造已部署成功、不复用源托管 URL。
 */
@Component
public class McpDeploymentAdapter {

    /**
     * 检查目标环境是否有可用的 NPX/UVX 托管部署能力。
     * 基线：返回 false（目标部署适配器未实现）。
     */
    public boolean isNpxUvxDeploymentAvailable() {
        return false;
    }

    /**
     * 目标部署可用性拒绝（导入 NPX/UVX 时调用）。
     */
    public AgentStudioException unavailable() {
        return new AgentStudioException(StudioError.MCP_DEPLOYMENT_UNAVAILABLE,
            "NPX/UVX target deployment adapter not available in this environment");
    }

    /**
     * orgType 是否属于需要目标托管部署的类型。
     */
    public static boolean requiresDeployment(String orgType) {
        return StringUtils.equalsAnyIgnoreCase(orgType, "NPX", "UVX");
    }
}

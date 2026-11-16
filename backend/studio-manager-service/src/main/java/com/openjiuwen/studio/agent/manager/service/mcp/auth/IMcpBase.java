/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.auth;


import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;

import java.util.Map;

public interface IMcpBase {

    String exchangeTokenByAuth(AuthInfo authInfo, Map<String, String> headers, String mcpUrl);

    AuthInfo anonymizeAuthInfo(AuthInfo authInfo);

    AuthInfo encryptedAuthInfo(AuthInfo authInfo);

    AuthInfo decryptedAuthInfo(AuthInfo authInfo);

    void validAuthInfo(AuthInfo authInfo);

    /**
     * FEAT-093 动态鉴权头 vs serverConfig 固定请求头同名拒绝
     * （scope=DYNAMIC 时比对 auth_keys[].target_name 与 serverConfig 的
     * headers 键，大小写不敏感，同名抛 MCP_AUTH_DATA_INVALID）。
     */
    void validDynamicAuthHeaderConflict(AuthInfo authInfo, String serverConfig);

    AuthInfo validIsNeedToUpdateAuthInfo(AuthInfo newAuth, AuthInfo oldAuth);

    String parseMcpInput2ResourceParameter(McpServiceEntity mcpService);

    void fillExtendInfoOfMcpWhenRetrieveAgent(MappingEntity agentMcp);

}

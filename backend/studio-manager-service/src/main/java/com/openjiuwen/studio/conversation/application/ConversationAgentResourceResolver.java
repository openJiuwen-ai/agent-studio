package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.service.IAgentManagementService;

import lombok.RequiredArgsConstructor;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 会话工作台用户应用二次校验。
 *
 * <p>资源查询、归属和版本数据复用 Agent 管理服务；会话模块不复制 Agent 发布逻辑。</p>
 */
@Component
@RequiredArgsConstructor
public class ConversationAgentResourceResolver {
    private static final String SINGLE_AGENT_TYPE = "agent";
    private static final String MULTI_AGENT_TYPE = "controller";

    private final IAgentManagementService agentManagementService;

    /**
     * 校验当前用户仍可执行指定应用。
     *
     * @return 已发布资源信息，供后续运行适配使用
     */
    public AgentInfo requirePublished(String projectId, String workspaceId, String appId) {
        if (StringUtils.isBlank(appId)) {
            throw invalid("app_id is required");
        }
        AgentInfo agent = agentManagementService.retrieveAgent(projectId, appId, workspaceId);
        if (agent == null || !isSupportedType(agent.getType())) {
            throw invalid("app_id is not a supported single or multi agent");
        }
        if (!CommonConstant.AGENT_PUBLISHED.equals(agent.getStatus())) {
            throw invalid("app_id is not published");
        }

        VersionListRsp versions = agentManagementService.listAgentVersions(projectId, appId,
            new ListAgentVersionsQo().setWorkspaceId(workspaceId).setOffset(0).setLimit(1));
        if (versions == null || versions.getVersionList() == null || versions.getVersionList().isEmpty()) {
            throw invalid("published app version is not available");
        }
        return agent;
    }

    private boolean isSupportedType(String type) {
        return SINGLE_AGENT_TYPE.equals(type) || MULTI_AGENT_TYPE.equals(type);
    }

    private AgentStudioException invalid(String message) {
        return new AgentStudioException(
            com.openjiuwen.studio.agent.common.enums.StudioError.METHOD_ARGUMENT_NOT_VALID,
            List.of(message));
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryServiceInstancesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryServiceInstanceResponseBody;

/**
 * 外部记忆服务实例管理
 */
public interface IMemoryServiceInstanceService {

    /**
     * 创建实例
     */
    CreateMemoryServiceInstanceResponseBody createInstance(String projectId, String workspaceId,
        CreateMemoryServiceInstanceRequestBody body);

    /**
     * 删除实例（删除前校验是否有记忆库在用）
     */
    void deleteInstance(String projectId, String instanceId, String workspaceId);

    /**
     * 修改实例
     */
    void modifyInstance(String projectId, String instanceId, String workspaceId,
        ModifyMemoryServiceInstanceRequestBody body);

    /**
     * 查询实例列表
     */
    ListMemoryServiceInstancesResponseBody listInstances(String projectId, String workspaceId, String name);

    /**
     * 查询实例详情
     */
    ShowMemoryServiceInstanceResponseBody showInstance(String projectId, String instanceId, String workspaceId);

    /**
     * 健康检查（调 agent-memory GET /health）
     */
    ShowMemoryServiceInstanceResponseBody healthCheck(String projectId, String instanceId, String workspaceId);

    /**
     * 向实例推送 scope 级模型配置（POST /set_scope_config）
     *
     * @param instanceId      实例ID
     * @param scopeId         scope_id（= memory_repo_id）
     * @param scopeModelConfig 模型配置JSON
     */
    void pushScopeConfig(String instanceId, String scopeId, String scopeModelConfig);

    /**
     * 删除实例上指定 scope 的所有记忆数据（POST /delete_mem_by_scope）
     *
     * @param instanceId 实例ID
     * @param scopeId   scope_id（= memory_repo_id）
     */
    void deleteMemByScope(String instanceId, String scopeId);
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.BatchDeleteMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryItemResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SearchMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateMemoryItemRequestBody;

public interface IMemoryItemManagementService {

    ListMemoryItemResponseBody listMemoryItems(String projectId, String memoryRepoId, Integer pageNum,
        Integer pageSize, String memoryType);

    void deleteMemoryItem(String projectId, String memoryRepoId, String memoryId);

    void batchDeleteMemoryItems(String projectId, String memoryRepoId, BatchDeleteMemoryItemRequestBody body);

    ListMemoryItemResponseBody searchMemoryItems(String projectId, String memoryRepoId, SearchMemoryItemRequestBody body);

    /**
     * 批量修改当前用户的记忆条目内容。
     * 采用保守策略：任意一条失败则整体失败，并记录失败条目id（已成功条目不回滚）。
     */
    void updateMemoryItems(String projectId, String memoryRepoId, UpdateMemoryItemRequestBody body);

    /**
     * 清空当前用户在指定记忆库下的全部记忆条目。
     */
    void clearUserMemoryItems(String projectId, String memoryRepoId);
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.bo;

import com.openjiuwen.studio.agent.manager.dto.ExtraMsg;
import com.openjiuwen.studio.agent.common.dto.ImportRes;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 工作流导入中间数据
 *
 */
@Data
public class WfImportDataWrapper {
    private Set<ExtraMsg> innerPluginsMsg = new HashSet<>();

    private Set<ExtraMsg> pluginsOfAuth = new HashSet<>();

    private Set<ExtraMsg> mcpsOfAuth = new HashSet<>();

    private Map<String, String> idToUuid = new HashMap<>();

    private List<String> succeedIds = new ArrayList<>();

    private List<String> failedIds = new ArrayList<>();

    private List<String> importedIds = new ArrayList<>();

    private List<String> updatedIds = new ArrayList<>();

    private List<String> skippedIds = new ArrayList<>();

    /**
     * 待导入工作流列表
     */
    private List<String> importWorkflowList = new ArrayList<>();

    private List<String> importAgentList = new ArrayList<>();

    private List<String> importToolList = new ArrayList<>();

    private List<String> importPluginList = new ArrayList<>();

    private List<ImportRes> importResList = new ArrayList<>();
}

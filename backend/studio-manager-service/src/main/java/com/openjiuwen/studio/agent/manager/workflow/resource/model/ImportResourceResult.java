/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.resource.model;

import lombok.Data;

@Data
public class ImportResourceResult {

    private String id;

    private String name;

    private String type;

    private String description;

    private String version;

    private String status;

    private String errorMsg;

    /**
     * 建议
     */
    private String suggestion;

    /**
     * 配置按钮(插件和供应商展示权限配置页面需要)
     */
    private Boolean configDisplay = false;

    private String newVersion;

    private String newId;

    private String newName;

    /**
     * 有效性,默认有效
     */
    private boolean valid = true;

    /**
     * 是否为首次导入（新建资源）。insertWorkflow/createController 首次导入时设 true，
     * update 不设（默认 false）。用于 handleResourceDsl 判断是否上传草稿 DSL：
     * 已发布版本导入到已有资源时跳过草稿上传，避免覆盖用户草稿。
     */
    private Boolean addTag = false;

}

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

    private Boolean addTag = false;

}

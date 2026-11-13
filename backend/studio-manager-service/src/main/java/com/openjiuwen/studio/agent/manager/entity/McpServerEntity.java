/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

@NoArgsConstructor
@AllArgsConstructor
@Data
@EqualsAndHashCode(callSuper = true)
public class McpServerEntity extends BaseProperties {
    /**
     * 主键uuid
     */
    private String id;

    /**
     * MCP标识
     */
    private String serverCode;

    /**
     * ICON 图标
     */
    private String icon;

    /**
     * name 中文名
     */
    private String name;

    /**
     * name 英文名
     */
    private String nameEn;

    /**
     * 描述、简介-中文
     */
    private String description;

    /**
     * 描述、简介-英文
     */
    private String descriptionEn;

    /**
     * 概述 Markdown
     */
    private String readme;

    /**
     * 官方地址，一般是github地址
     */
    private String url;

    /**
     * MCP安装配置
     */
    private String serverConfig;

    /**
     * MCP工具集 JSON存储
     */
    private String tools;

    /**
     * 内置 OR 个人
     */
    private String type;

    /**
     * MCP安装类型  NPX/UVX/SSE
     */
    private String orgType;

    /**
     * 查看次数
     */
    private long viewTimes;

    /**
     * 安装次数
     */
    private long installTimes;

    /**
     * 类别
     */
    private String category;

    /**
     * 用户上架到资产广场标记（1=是，0=否）；官方预置 type=inner 不受此列影响
     */
    private Integer platformPublished;

    /**
     * 上架来源的MCP服务实例ID（ws_mcp_service_def.id），用于同一实例重复上架去重
     */
    private String sourceInstanceId;

}


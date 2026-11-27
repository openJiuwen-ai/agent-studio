/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * FEAT-134 MCP 服务导出请求。
 *
 * selection=IDS 时 service_ids 必填（1～100 去重）；selection=ALL 时 service_ids 必须为空，
 * 表示当前工作空间内全部可管理的普通 MCP 实例（与分页/搜索过滤无关）。
 */
public class McpTransferExportReq {

    /** 选择模式：IDS / ALL */
    public static final String SELECTION_IDS = "IDS";
    public static final String SELECTION_ALL = "ALL";

    @JsonProperty("selection")
    @NotBlank
    private String selection;

    @JsonProperty("service_ids")
    @Valid
    @Size(max = 100)
    private List<String> serviceIds;

    public String getSelection() {
        return selection;
    }

    public McpTransferExportReq setSelection(String selection) {
        this.selection = selection;
        return this;
    }

    public List<String> getServiceIds() {
        return serviceIds;
    }

    public McpTransferExportReq setServiceIds(List<String> serviceIds) {
        this.serviceIds = serviceIds;
        return this;
    }
}

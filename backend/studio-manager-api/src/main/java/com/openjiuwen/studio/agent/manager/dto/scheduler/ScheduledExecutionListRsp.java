/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.scheduler;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.List;

/**
 * 自动化任务执行日志分页响应。
 */
@Data
public class ScheduledExecutionListRsp {
    @JsonProperty("items")
    private List<ScheduledExecutionRsp> items;

    @JsonProperty("total")
    private long total;

    @JsonProperty("page")
    private int page;

    @JsonProperty("page_size")
    private int pageSize;
}

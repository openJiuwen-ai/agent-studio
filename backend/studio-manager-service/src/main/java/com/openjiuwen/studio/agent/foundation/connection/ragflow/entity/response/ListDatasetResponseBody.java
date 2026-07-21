/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.connection.ragflow.entity.response;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import lombok.Data;

import java.util.List;

/**
 * 查询RAGFlow数据集列表响应消息体
 *
 * @since 2025-07-21
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ListDatasetResponseBody {

    private Integer code;

    private List<DatasetBasicInfo> data;

    private String message;

    /**
     * 满足过滤条件的数据集总数，用于服务端分页
     */
    private Long totalDatasets;
}

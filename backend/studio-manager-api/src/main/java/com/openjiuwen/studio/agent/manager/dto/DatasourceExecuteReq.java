/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

@Data
public class DatasourceExecuteReq implements Serializable {
    private static final long serialVersionUID = 1L;

    private String query;

    private List<String> conditions;
}

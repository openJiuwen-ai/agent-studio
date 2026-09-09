/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
public class DatasourceExecuteResp implements Serializable {
    private static final long serialVersionUID = 1L;

    private List<Map<String, Object>> outputList = new ArrayList<>();

    private int rowNum;
}

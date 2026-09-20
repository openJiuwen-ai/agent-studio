/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

@Data
public class DatasourceListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    private int total;

    private List<DatasourceInfoRsp> datasources;
}

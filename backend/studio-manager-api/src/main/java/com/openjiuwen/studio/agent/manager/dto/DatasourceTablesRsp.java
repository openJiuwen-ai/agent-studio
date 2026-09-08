/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

@Data
public class DatasourceTablesRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    private List<String> tables;
}

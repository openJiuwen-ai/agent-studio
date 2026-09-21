/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class DatasourceInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    private String name;

    private String type;

    private String desc;

    private DatasourceConnectionInfo connectionInfo;
}

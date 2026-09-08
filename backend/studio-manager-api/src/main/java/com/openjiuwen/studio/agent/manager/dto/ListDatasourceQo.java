/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class ListDatasourceQo implements Serializable {
    private static final long serialVersionUID = 1L;

    private Integer page = 1;

    private Integer pageSize = 20;

    private String name;

    private String type;

    private String status;
}

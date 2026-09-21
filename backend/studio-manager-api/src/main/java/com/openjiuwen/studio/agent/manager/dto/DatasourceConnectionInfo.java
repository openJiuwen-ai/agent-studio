/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Data;

import java.io.Serializable;
import java.util.Map;

@Data
public class DatasourceConnectionInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    private String host;

    private String port;

    private String databaseName;

    private String user;

    private String password;

    private boolean sslEnabled;

    private String sqlVersion;

    private Map<String, String> metadata;
}

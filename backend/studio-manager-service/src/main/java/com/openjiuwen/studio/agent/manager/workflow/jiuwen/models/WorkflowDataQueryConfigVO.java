/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.jiuwen.models;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 * 可视化查询条件配置
 *
 */
@Data
public class WorkflowDataQueryConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    private String logic;

    private List<Condition> conditions;

    private List<Order> orders;

    private Integer limit;

    private Integer offset;

    @Data
    public static class Condition implements Serializable {
        private static final long serialVersionUID = 1L;

        private String field;

        private String operator;

        private Object value;
    }

    @Data
    public static class Order implements Serializable {
        private static final long serialVersionUID = 1L;

        private String field;

        private Boolean asc;
    }
}

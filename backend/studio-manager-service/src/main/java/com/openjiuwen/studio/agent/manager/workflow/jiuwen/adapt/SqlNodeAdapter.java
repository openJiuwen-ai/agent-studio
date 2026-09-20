/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.SqlKeywordEnum;
import com.openjiuwen.studio.agent.common.enums.SqlOperatorType;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.WorkflowDataQueryConfigVO;

import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * SQL节点转换IR
 *
 */
public class SqlNodeAdapter extends AbstractIRNodeAdapter {

    private static final String DATASOURCE_ID = "id";

    private static final String SQL = "sql";

    private static final String CONDITIONS = "conditions";

    private static final String SELECT_QUERY = "select_query";

    private static final String OUTPUT_COLUMN = "output_column";

    private static final String TABLE_NAME = "table_name";

    private static final String SELECT_TEMPLATE = "SELECT %s FROM `%s`";

    private static final String ALL_COLUMNS = "*";

    @Override
    public Map<String, Object> adaptConfig(WorkflowNodeVO workflowNodeVo) {
        Map<String, Object> nodeConfigs = workflowNodeVo.getConfigs();
        Map<String, Object> configs = new HashMap<>();

        configs.put(DATASOURCE_ID, nodeConfigs.get(DATASOURCE_ID));

        if (nodeConfigs.get(SELECT_QUERY) != null) {
            String selectColumn = constructColumnByList(nodeConfigs.get(OUTPUT_COLUMN));
            List<String> conditions = new ArrayList<>();
            WorkflowDataQueryConfigVO queryConfig =
                JsonUtils.objectToClassType(nodeConfigs.get(SELECT_QUERY), WorkflowDataQueryConfigVO.class);
            String sql = String.format(SELECT_TEMPLATE, selectColumn, nodeConfigs.get(TABLE_NAME))
                + adaptExpression(queryConfig, conditions);
            configs.put(SQL, sql);
            configs.put(CONDITIONS, conditions);
        } else {
            configs.put(SQL, nodeConfigs.get(SQL));
        }
        return configs;
    }

    @Override
    public String getNodeType() {
        return NodeType.SQL.getIrType();
    }

    private String constructColumnByList(Object outputColumn) {
        if (outputColumn == null) {
            return ALL_COLUMNS;
        }
        List<String> columns = JsonUtils.objectToClass(outputColumn);
        if (columns == null || columns.isEmpty()) {
            return ALL_COLUMNS;
        }
        return columns.stream()
            .filter(StringUtils::isNotBlank)
            .map(col -> "`" + col + "`")
            .collect(Collectors.joining(", "));
    }

    private String adaptExpression(WorkflowDataQueryConfigVO queryConfig, List<String> conditions) {
        if (queryConfig == null) {
            return StringUtils.EMPTY;
        }
        StringBuilder sb = new StringBuilder();

        adaptWhereClause(queryConfig, conditions, sb);
        adaptOrderByClause(queryConfig, sb);
        adaptLimitClause(queryConfig, sb);
        adaptOffsetClause(queryConfig, sb);

        return sb.toString();
    }

    private void adaptWhereClause(WorkflowDataQueryConfigVO queryConfig, List<String> conditions, StringBuilder sb) {
        List<WorkflowDataQueryConfigVO.Condition> conditionList = queryConfig.getConditions();
        if (conditionList == null || conditionList.isEmpty()) {
            return;
        }
        sb.append(SqlKeywordEnum.WHERE.getValue());

        String logic = queryConfig.getLogic();
        String connector = StringUtils.isNotEmpty(logic)
            ? SqlKeywordEnum.valueOf(logic.toUpperCase()).getValue() : SqlKeywordEnum.AND.getValue();

        List<String> clauses = new ArrayList<>();
        for (WorkflowDataQueryConfigVO.Condition condition : conditionList) {
            String clause = adaptCondition(condition, conditions);
            if (StringUtils.isNotEmpty(clause)) {
                clauses.add(clause);
            }
        }

        if (!clauses.isEmpty()) {
            sb.append(String.join(connector.trim() + " ", clauses));
        }
    }

    private String adaptCondition(WorkflowDataQueryConfigVO.Condition condition, List<String> conditions) {
        String field = condition.getField();
        String operatorType = condition.getOperator();
        if (StringUtils.isBlank(field) || StringUtils.isBlank(operatorType)) {
            return StringUtils.EMPTY;
        }

        SqlOperatorType operator = SqlOperatorType.valueOf(operatorType.toUpperCase());
        String template = operator.getTemplate();

        switch (operator) {
            case IS_NULL, IS_NOT_NULL -> {
                return String.format(template, "`" + field + "`");
            }
            case IN, NOT_IN -> {
                List<String> values = JsonUtils.objectToClass(condition.getValue());
                if (values == null || values.isEmpty()) {
                    return StringUtils.EMPTY;
                }
                String placeholders = values.stream().map(v -> "?").collect(Collectors.joining(", "));
                values.forEach(conditions::add);
                return String.format(template, "`" + field + "`", "(" + placeholders + ")");
            }
            case LIKE, NOT_LIKE -> {
                String value = String.valueOf(condition.getValue());
                conditions.add("%" + value + "%");
                return String.format(template, "`" + field + "`");
            }
            default -> {
                conditions.add(String.valueOf(condition.getValue()));
                return String.format(template, "`" + field + "`");
            }
        }
    }

    private void adaptOrderByClause(WorkflowDataQueryConfigVO queryConfig, StringBuilder sb) {
        List<WorkflowDataQueryConfigVO.Order> orders = queryConfig.getOrders();
        if (orders == null || orders.isEmpty()) {
            return;
        }
        sb.append(SqlKeywordEnum.ORDER_BY.getValue());
        String orderStr = orders.stream()
            .filter(order -> StringUtils.isNotBlank(order.getField()))
            .map(order -> "`" + order.getField() + "`" + (Boolean.TRUE.equals(order.getAsc())
                ? SqlKeywordEnum.ASC.getValue() : SqlKeywordEnum.DESC.getValue()))
            .collect(Collectors.joining(", "));
        sb.append(orderStr);
    }

    private void adaptLimitClause(WorkflowDataQueryConfigVO queryConfig, StringBuilder sb) {
        if (queryConfig.getLimit() != null && queryConfig.getLimit() > 0) {
            sb.append(SqlKeywordEnum.LIMIT.getValue()).append(queryConfig.getLimit());
        }
    }

    private void adaptOffsetClause(WorkflowDataQueryConfigVO queryConfig, StringBuilder sb) {
        if (queryConfig.getOffset() != null && queryConfig.getOffset() >= 0) {
            sb.append(SqlKeywordEnum.OFFSET.getValue()).append(queryConfig.getOffset());
        }
    }
}

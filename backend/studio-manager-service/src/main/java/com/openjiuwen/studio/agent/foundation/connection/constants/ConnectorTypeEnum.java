/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.connection.constants;

import lombok.Getter;

/**
 * 当前支持的连接器类型
 *
 * @since 2025-08-25
 */
@Getter
public enum ConnectorTypeEnum {
    // outside的连接器类型为非全量接口接入，仅包含检索接口
    LAKE_SEARCH("LakeSearch", "outside"),
    KOO_SEARCH("KooSearch", "outside"),
    RAG_FLOW("Ragflow", "outside"),
    HIS("His", "outside"),
    GENERAL("General", "outside"),
    // inside的连接器类型为全量接口接入，包含管理面接口和检索接口
    AGENT_BASE_RAG("AgentBaseRag", "inside"),
    LAKE_SEARCH_INSIDE("LakeSearchInside", "inside"),
    KOO_SEARCH_INSIDE("KooSearchInside", "inside"),
    OPENJIUWEN_INSIDE("OpenjiuwenInside", "inside"),
    CUSTOM("Custom", "inside");

    private final String value;

    private final String type;

    ConnectorTypeEnum(String value, String type) {
        this.value = value;
        this.type = type;
    }

    public static ConnectorTypeEnum fromValue(String value) {
        for (ConnectorTypeEnum connectorTypeEnum : ConnectorTypeEnum.values()) {
            if (connectorTypeEnum.getValue().equals(value)) {
                return connectorTypeEnum;
            }
        }
        return null;
    }
}

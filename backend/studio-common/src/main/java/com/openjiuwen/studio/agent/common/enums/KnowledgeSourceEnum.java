/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.enums;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 知识库来源枚举
 *
 */
public enum KnowledgeSourceEnum {
    /**
     * KooSearch知识库
     */
    KOOSEARCH("KooSearch"),

    /**
     * LakeSearch知识库
     */
    LAKESEARCH("LakeSearch"),

    /**
     * CUSTOM知识库
     */
    CUSTOM("CUSTOM"),

    /**
     * OpenJiuwen本地知识库
     */
    OPENJIUWEN("OpenJiuwen");

    /**
     * 知识库类型
     */
    private final String source;

    KnowledgeSourceEnum(String source) {
        this.source = source;
    }

    @Override
    @JsonValue
    public String toString() {
        return source;
    }

    /**
     * 根据source枚举值，获取KnowledgeSourceEnum枚举对象
     *
     * @param source 知识库类型
     * @return KnowledgeSourceEnum
     */
    @JsonCreator
    public static KnowledgeSourceEnum fromValue(String source) {
        for (KnowledgeSourceEnum knowledgeSource : KnowledgeSourceEnum.values()) {
            if (knowledgeSource.source.equalsIgnoreCase(source)) {
                return knowledgeSource;
            }
        }
        return null;
    }
}

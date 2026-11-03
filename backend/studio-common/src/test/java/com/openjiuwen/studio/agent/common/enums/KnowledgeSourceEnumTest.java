/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.enums;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class KnowledgeSourceEnumTest {

    @Test
    void testValues() {
        assertEquals(4, KnowledgeSourceEnum.values().length);
    }

    @Test
    void testValueOf() {
        assertEquals(KnowledgeSourceEnum.KOOSEARCH, KnowledgeSourceEnum.valueOf("KOOSEARCH"));
        assertEquals(KnowledgeSourceEnum.LAKESEARCH, KnowledgeSourceEnum.valueOf("LAKESEARCH"));
        assertEquals(KnowledgeSourceEnum.CUSTOM, KnowledgeSourceEnum.valueOf("CUSTOM"));
        assertEquals(KnowledgeSourceEnum.OPENJIUWEN, KnowledgeSourceEnum.valueOf("OPENJIUWEN"));
    }

    @Test
    void testFromValue_Existing() {
        assertEquals(KnowledgeSourceEnum.KOOSEARCH, KnowledgeSourceEnum.fromValue("KooSearch"));
        assertEquals(KnowledgeSourceEnum.LAKESEARCH, KnowledgeSourceEnum.fromValue("LakeSearch"));
        assertEquals(KnowledgeSourceEnum.CUSTOM, KnowledgeSourceEnum.fromValue("CUSTOM"));
        assertEquals(KnowledgeSourceEnum.OPENJIUWEN, KnowledgeSourceEnum.fromValue("OpenJiuwen"));
    }

    @Test
    void testFromValue_CaseInsensitive() {
        assertEquals(KnowledgeSourceEnum.KOOSEARCH, KnowledgeSourceEnum.fromValue("koosearch"));
        assertEquals(KnowledgeSourceEnum.CUSTOM, KnowledgeSourceEnum.fromValue("custom"));
    }

    @Test
    void testFromValue_NonExisting() {
        assertNull(KnowledgeSourceEnum.fromValue("unknown"));
    }

    @Test
    void testToString() {
        assertEquals("KooSearch", KnowledgeSourceEnum.KOOSEARCH.toString());
        assertEquals("LakeSearch", KnowledgeSourceEnum.LAKESEARCH.toString());
        assertEquals("CUSTOM", KnowledgeSourceEnum.CUSTOM.toString());
        assertEquals("OpenJiuwen", KnowledgeSourceEnum.OPENJIUWEN.toString());
    }
}

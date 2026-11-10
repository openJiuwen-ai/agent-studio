/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * COM-04 §5.2 修订（2026-11-02）：RUNTIME 码形信任门矩阵。
 * <p>
 * 码形门须同时满足：①不吃 Runtime 引擎 6 位码族与 999999 兜底；②信任
 * error_contract 12 族与应用层 0 头 8 位族；③Builder canonical 13 头码族
 * 到 RUNTIME 身份不跨服务误信（2026-10-27 格式门的回归点）。
 */
class DownstreamErrorMappingCatalogTest {

    private DownstreamErrorMappingCatalog catalog;

    @BeforeEach
    void setUp() {
        catalog = new DownstreamErrorMappingCatalog(new ManagerErrorCatalog());
    }

    // ---- RUNTIME：应信任的码形 ----

    @ParameterizedTest
    @ValueSource(strings = {
        // 引擎/组件 6 位码族（100000~129999）
        "openjiuwen.100000", "openjiuwen.101003", "openjiuwen.101905",
        "openjiuwen.109300", "openjiuwen.120007",
        // Runtime 未知码兜底
        "openjiuwen.999999",
        // error_contract 自有目录（7 位 121007 / 8 位 12100001~06）
        "openjiuwen.121007", "openjiuwen.12100001", "openjiuwen.12100006",
        // 应用层 0 头 8 位码族（与 Manager i18n 共库）
        "openjiuwen.02001003", "openjiuwen.02201021", "openjiuwen.02501037"
    })
    void runtime_canonical_shapes_are_trusted(String code) {
        assertTrue(catalog.isRecognizedDownstreamCode(DownstreamService.RUNTIME, code),
            "RUNTIME canonical 码形应被信任: " + code);
        assertTrue(catalog.isRuntimeCanonicalShape(code));
    }

    // ---- RUNTIME：应拒绝的码形（含 Builder 13 头跨服务误信回归） ----

    @ParameterizedTest
    @ValueSource(strings = {
        // Builder canonical 族——跨服务不信任（修复 2026-10-27 格式门回归）
        "openjiuwen.13100006", "openjiuwen.13100013", "openjiuwen.13100099",
        // 6 位但非引擎段/非兜底
        "openjiuwen.999998", "openjiuwen.130001", "openjiuwen.900000",
        // 7 位非 12 头
        "openjiuwen.2010001", "openjiuwen.0101001",
        // 8 位非 0 头/12 头
        "openjiuwen.21010001", "openjiuwen.10100003",
        // 无前缀 / 大小写 / 空白 / 非纯数字
        "101003", "OPENJIUWEN.101003", "openjiuwen.10100a", "openjiuwen. 101003",
        "openjiuwen.101003 ", "openjiuwen.-101003", "openjiuwen..101003"
    })
    void runtime_non_canonical_shapes_rejected(String code) {
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.RUNTIME, code),
            "RUNTIME 非法码形应被拒绝: " + code);
        assertFalse(catalog.isRuntimeCanonicalShape(code));
    }

    // ---- 边界 ----

    @Test
    void runtime_null_or_blank_code_rejected() {
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.RUNTIME, null));
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.RUNTIME, ""));
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.RUNTIME, "   "));
        assertFalse(catalog.isRuntimeCanonicalShape(null));
        assertFalse(catalog.isRuntimeCanonicalShape(""));
    }

    // ---- Builder：精确码表不变 ----

    @ParameterizedTest
    @ValueSource(strings = {
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013"
    })
    void builder_canonical_codes_still_trusted(String code) {
        assertTrue(catalog.isRecognizedDownstreamCode(DownstreamService.BUILDER, code));
    }

    @Test
    void builder_runtime_shaped_code_not_trusted_on_builder_service() {
        // 引擎码形在 BUILDER 身份上不信任（精确码表语义不变）
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.BUILDER, "openjiuwen.101003"));
        assertFalse(catalog.isRecognizedDownstreamCode(DownstreamService.BUILDER, "openjiuwen.02001003"));
    }
}

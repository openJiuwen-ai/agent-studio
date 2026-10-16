/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.filter.SnakeToCamelCompatibleConfig;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentsListQo;

import jakarta.validation.Valid;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * QueryEnvironmentsListQo 查询参数绑定测试（is_default → isDefault）。
 *
 * 环境列表接口按 query object 绑定 QO，@JsonProperty("is_default") 不参与该绑定；
 * 前端发送的 snake_case 参数依赖全局 SnakeToCamelCompatibleConfig 过滤器补
 * camelCase 别名后按 JavaBean 属性名绑定。本测试在真实 MVC 绑定管线
 * （standalone MockMvc + 该过滤器 + QO 形参）上验证绑定成立，防止过滤器或
 * QO getter/setter 重构时静默断链（默认环境兜底与 is_default 过滤的前提）。
 */
class QueryEnvironmentsListQoBindingTest {

    private final AtomicReference<QueryEnvironmentsListQo> boundQo = new AtomicReference<>();

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(new BindingController(boundQo))
            .addFilters(new SnakeToCamelCompatibleConfig.SnakeToCamelCompatibleFilter())
            .build();
    }

    @RestController
    static class BindingController {

        private final AtomicReference<QueryEnvironmentsListQo> boundQo;

        BindingController(AtomicReference<QueryEnvironmentsListQo> boundQo) {
            this.boundQo = boundQo;
        }

        @GetMapping("/bind")
        public String bind(@Valid QueryEnvironmentsListQo qo) {
            boundQo.set(qo);
            return "ok";
        }
    }

    @Test
    void testBind_IsDefaultFromSnakeCaseParam() throws Exception {
        mockMvc.perform(get("/bind").param("is_default", "true"))
            .andExpect(status().isOk());
        assertEquals(Boolean.TRUE, boundQo.get().getIsDefault());
    }

    @Test
    void testBind_IsDefaultFromCamelCaseParam() throws Exception {
        mockMvc.perform(get("/bind").param("isDefault", "true"))
            .andExpect(status().isOk());
        assertEquals(Boolean.TRUE, boundQo.get().getIsDefault());
    }

    @Test
    void testBind_IsDefaultFalseFromSnakeCaseParam() throws Exception {
        mockMvc.perform(get("/bind").param("is_default", "false"))
            .andExpect(status().isOk());
        assertEquals(Boolean.FALSE, boundQo.get().getIsDefault());
    }

    @Test
    void testBind_IsDefaultAbsentStaysNull() throws Exception {
        mockMvc.perform(get("/bind").param("limit", "20"))
            .andExpect(status().isOk());
        assertNull(boundQo.get().getIsDefault());
        assertEquals(Integer.valueOf(20), boundQo.get().getLimit());
    }

    @Test
    void testBind_OtherFieldsAlongsideSnakeCaseParam() throws Exception {
        mockMvc.perform(get("/bind").param("is_default", "true").param("name", "envA"))
            .andExpect(status().isOk());
        assertEquals(Boolean.TRUE, boundQo.get().getIsDefault());
        assertEquals("envA", boundQo.get().getName());
    }
}

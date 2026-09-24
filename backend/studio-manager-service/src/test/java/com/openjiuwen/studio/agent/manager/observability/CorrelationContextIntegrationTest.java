/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * COM-05 审视 T1：真实 Spring MVC 链集成验证。用 standaloneSetup 组建真实
 * DispatcherServlet/HandlerMapping/HandlerAdapter 链 + 手动加入关联 Filter 和
 * conversation 拦截器，证明单元测试的行为在实际 Spring MVC 组合链路中同样成立。
 */
class CorrelationContextIntegrationTest {

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(new TestController())
            .addInterceptors(new ConversationContextInterceptor())
            .addFilters(new CorrelationContextFilter())
            .setControllerAdvice(new TestExceptionHandler())
            .build();
    }

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    /** 正常请求：Controller 内 MDC 持有本次 request-id，响应回写同值。 */
    @Test
    void normalRequest_controllerSeesMdcAndResponseHasHeader() throws Exception {
        mockMvc.perform(get("/test/ok").header("X-Request-Id", "req-1"))
            .andExpect(status().isOk())
            .andExpect(content().string("req-1"))
            .andExpect(header().string("X-Request-Id", "req-1"))
            .andExpect(header().string("TraceID", "req-1"));
    }

    /** 缺失 Header：生成 UUID，trace 回退 request。 */
    @Test
    void missingHeaders_generatesUuid() throws Exception {
        mockMvc.perform(get("/test/ok"))
            .andExpect(status().isOk())
            .andExpect(result -> {
                String reqId = result.getResponse().getHeader("X-Request-Id");
                org.assertj.core.api.Assertions.assertThat(reqId).isNotEmpty();
                org.assertj.core.api.Assertions.assertThat(result.getResponse().getHeader("TraceID"))
                    .isEqualTo(reqId);
            });
    }

    /** 非法 Header：替换为 UUID，不回显非法原值。 */
    @Test
    void illegalHeader_replacedNotEchoed() throws Exception {
        mockMvc.perform(get("/test/ok").header("X-Request-Id", "bad value!"))
            .andExpect(status().isOk())
            .andExpect(header().string("X-Request-Id", org.hamcrest.Matchers.not("bad value!")));
    }

    /** 404：响应仍携带本次 request-id（Filter 在 doFilter 前已写 Header）。 */
    @Test
    void notFound_carriesSameHeader() throws Exception {
        mockMvc.perform(get("/test/nonexistent").header("X-Request-Id", "req-404"))
            .andExpect(status().isNotFound())
            .andExpect(header().string("X-Request-Id", "req-404"))
            .andExpect(header().string("TraceID", "req-404"));
    }

    /** Controller 抛异常：不重新选值，响应 Header 不变。 */
    @Test
    void controllerThrows_doesNotReselect() throws Exception {
        mockMvc.perform(get("/test/boom").header("X-Request-Id", "req-boom"))
            .andExpect(status().is5xxServerError())
            .andExpect(header().string("X-Request-Id", "req-boom"))
            .andExpect(header().string("TraceID", "req-boom"));
    }

    /** 未登记会话路由：拦截器 profileFor 返回 null，conversation-id 保持外层空值。 */
    @Test
    void unregisteredConversationRoute_keepsEmptyConversationMdc() throws Exception {
        mockMvc.perform(get("/test/conv/conv-1").header("X-Request-Id", "req-1"))
            .andExpect(status().isOk())
            .andExpect(content().string(""));
    }

    /** 405：POST 到 GET-only 路由仍携带同一组关联 Header。 */
    @Test
    void methodNotAllowed_carriesSameHeader() throws Exception {
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                .post("/test/ok").header("X-Request-Id", "req-405"))
            .andExpect(status().isMethodNotAllowed())
            .andExpect(header().string("X-Request-Id", "req-405"))
            .andExpect(header().string("TraceID", "req-405"));
    }

    /** 认证短路：受控认证 Filter 返回 401 不继续 chain，双 Header + Filter 内 MDC 可见 + 退出恢复。 */
    @Test
    void authShortCircuit_dualHeaderAndMdcAndRestore() throws Exception {
        final String[] mdcDuringAuth = {null};
        jakarta.servlet.Filter authFilter = new jakarta.servlet.Filter() {
            @Override
            public void doFilter(jakarta.servlet.ServletRequest req, jakarta.servlet.ServletResponse res,
                jakarta.servlet.FilterChain chain) {
                mdcDuringAuth[0] = MDC.get(MdcKeys.REQUEST_ID);
                ((jakarta.servlet.http.HttpServletResponse) res).setStatus(401);
            }
            @Override
            public void init(jakarta.servlet.FilterConfig fc) { }
            @Override
            public void destroy() { }
        };
        MockMvc authMvc = org.springframework.test.web.servlet.setup.MockMvcBuilders
            .standaloneSetup(new TestController())
            .addFilters(new CorrelationContextFilter(), authFilter)
            .build();

        authMvc.perform(get("/test/ok").header("X-Request-Id", "req-401"))
            .andExpect(status().isUnauthorized())
            .andExpect(header().string("X-Request-Id", "req-401"))
            .andExpect(header().string("TraceID", "req-401"));
        // 认证 Filter 内 MDC 持有本次 request-id
        org.assertj.core.api.Assertions.assertThat(mdcDuringAuth[0]).isEqualTo("req-401");
        // 退出后恢复入站前状态
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    /** 有效会话 scope 行为已在 ConversationContextInterceptorTest 充分覆盖
     * （Interceptor 对注册路由安装 conversation-id、同步/异步/ERROR 关闭、幂等）。
     * 此处 TestController 路由不在 ConversationIdValidator 注册表，保持空值——
     * 参见 {@link #unregisteredConversationRoute_keepsEmptyConversationMdc}。 */

    /** 线程复用：第二请求看不到第一请求的 ID。 */
    @Test
    void threadReuse_secondRequestSeesNoFirstRequestIds() throws Exception {
        mockMvc.perform(get("/test/ok").header("X-Request-Id", "req-a"))
            .andExpect(content().string("req-a"));
        mockMvc.perform(get("/test/ok").header("X-Request-Id", "req-b"))
            .andExpect(content().string("req-b"));
    }

    /** 预置历史 MDC：Filter 进入后清场，退出后恢复入站前状态。 */
    @Test
    void presetHistory_clearedDuringRequest_restoredAfter() throws Exception {
        MDC.put(MdcKeys.REQUEST_ID, "old-req");
        MDC.put(MdcKeys.EXECUTION_ID, "residue-exec");
        MDC.put(MdcKeys.CONVERSATION_ID, "residue-conv");

        mockMvc.perform(get("/test/ok").header("X-Request-Id", "req-1"))
            .andExpect(content().string("req-1"));

        // 退出后恢复入站前
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("old-req");
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("residue-exec");
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("residue-conv");
    }

    /** §4.2.2 参数校验失败：@RequestBody @Valid 缺必填字段返回 400，Header 不变。 */
    @Test
    void parameterValidationFailure_carriesSameHeader() throws Exception {
        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                .post("/test/valid").header("X-Request-Id", "req-400")
                .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isBadRequest())
            .andExpect(header().string("X-Request-Id", "req-400"))
            .andExpect(header().string("TraceID", "req-400"));
    }

    /** §4.2.3/§5.2 未处理异常：异常传播瞬间 MDC + Header 仍有效，异常后 MDC 恢复。 */
    @Test
    void unhandledException_mdcAndHeaderDuringPropagation() {
        final String[] mdcDuringException = {null};
        final String[] headerDuringException = {null};
        jakarta.servlet.Filter observeFilter = new jakarta.servlet.Filter() {
            @Override
            public void doFilter(jakarta.servlet.ServletRequest req, jakarta.servlet.ServletResponse res,
                jakarta.servlet.FilterChain chain)
                throws java.io.IOException, jakarta.servlet.ServletException {
                try {
                    chain.doFilter(req, res);
                } catch (java.lang.Exception e) {
                    mdcDuringException[0] = MDC.get(MdcKeys.REQUEST_ID);
                    headerDuringException[0] =
                        ((jakarta.servlet.http.HttpServletResponse) res).getHeader("X-Request-Id");
                    throw e;
                }
            }
            @Override
            public void init(jakarta.servlet.FilterConfig fc) { }
            @Override
            public void destroy() { }
        };
        MockMvc observeMvc = MockMvcBuilders.standaloneSetup(new TestController())
            .addFilters(new CorrelationContextFilter(), observeFilter)
            .setControllerAdvice(new TestExceptionHandler())
            .build();

        org.assertj.core.api.Assertions.assertThatThrownBy(() ->
                observeMvc.perform(get("/test/unhandled").header("X-Request-Id", "req-unhandled")))
            .isInstanceOf(jakarta.servlet.ServletException.class);
        // 异常传播瞬间关联上下文仍有效
        org.assertj.core.api.Assertions.assertThat(mdcDuringException[0]).isEqualTo("req-unhandled");
        org.assertj.core.api.Assertions.assertThat(headerDuringException[0]).isEqualTo("req-unhandled");
        // 异常后 MDC 恢复入站前状态
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    /** §4.2.5 execution 嵌套：Controller 内层 execution scope 与外层 Filter scope 按所有权恢复。 */
    @Test
    void executionNestedScope_restoredInOrder() throws Exception {
        MDC.put(MdcKeys.EXECUTION_ID, "residue-exec");

        mockMvc.perform(get("/test/nested").header("X-Request-Id", "req-1"))
            .andExpect(status().isOk())
            .andExpect(content().string("exec-1"));

        // Controller 内层 execution scope 关闭→回到外层 Filter scope 空值→Filter close 后恢复入站前
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("residue-exec");
    }

    /** §4.2.6 ASYNC：第一次派发 asyncStarted + Header 写入；asyncDispatch 复用关联值；MDC 恢复。 */
    @Test
    void asyncDispatch_completesAndReusesCorrelation() throws Exception {
        org.springframework.test.web.servlet.MvcResult result = mockMvc.perform(
                get("/test/async").header("X-Request-Id", "req-async"))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.request()
                .asyncStarted())
            .andExpect(header().string("X-Request-Id", "req-async"))
            .andReturn();

        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                .asyncDispatch(result))
            .andExpect(status().isOk())
            .andExpect(content().string("async-result"))
            .andExpect(header().string("X-Request-Id", "req-async"));

        // 异步完成后 MDC 恢复入站前状态
        org.assertj.core.api.Assertions.assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    // ---- 最小测试 Controller ----

    @RestController
    @RequestMapping("/test")
    static class TestController {

        @GetMapping("/ok")
        public String ok() {
            return MDC.get(MdcKeys.REQUEST_ID);
        }

        @GetMapping("/conv/{conversation_id}")
        public String conv(@PathVariable("conversation_id") String conversationId) {
            return MDC.get(MdcKeys.CONVERSATION_ID);
        }

        @GetMapping("/boom")
        public String boom() {
            throw new IllegalStateException("boom");
        }

        /** 不被 ControllerAdvice 捕获的异常——验证异常后 MDC 恢复。 */
        @GetMapping("/unhandled")
        public String unhandled() {
            throw new IllegalArgumentException("not handled by advice");
        }

        /** 内层 execution scope 嵌套——模拟 DEF-02 execution scope。 */
        @GetMapping("/nested")
        public String nested() {
            try (MdcScope exec = MdcScope.open(java.util.Map.of(MdcKeys.EXECUTION_ID, "exec-1"))) {
                return MDC.get(MdcKeys.EXECUTION_ID);
            }
        }

        /** 参数校验失败——@RequestBody @Valid 缺必填字段。 */
        @org.springframework.web.bind.annotation.PostMapping("/valid")
        public String valid(@jakarta.validation.Valid @org.springframework.web.bind.annotation.RequestBody
            ValidDto dto) {
            return MDC.get(MdcKeys.REQUEST_ID);
        }

        /** 异步请求——验证 afterConcurrentHandlingStarted 关闭 Servlet 线程 scope + 后续派发复用关联值。 */
        @GetMapping("/async")
        public java.util.concurrent.Callable<String> async() {
            return () -> "async-result";
        }
    }

    static class ValidDto {
        @jakarta.validation.constraints.NotBlank
        private String name;
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    @org.springframework.web.bind.annotation.ControllerAdvice
    static class TestExceptionHandler {
        @org.springframework.web.bind.annotation.ExceptionHandler(IllegalStateException.class)
        public org.springframework.http.ResponseEntity<String> handle(IllegalStateException e) {
            return org.springframework.http.ResponseEntity.status(500).body("boom");
        }
    }
}

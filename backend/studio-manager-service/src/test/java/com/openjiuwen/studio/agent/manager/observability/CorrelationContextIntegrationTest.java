/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import static org.assertj.core.api.Assertions.assertThat;
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

    /**
     * SUT-01 CD-013：完整 Header 列表断言（非 getFirst）。双写会让列表含 2 个同值，
     * {@code containsExactly} 严格捕获。§4.4 禁止只断言 getFirst。
     */
    private static void assertSingleCorrelation(MvcResult result, String expectedReqId, String expectedTraceId) {
        assertThat(result.getResponse().getHeaders("X-Request-Id"))
            .containsExactly(expectedReqId);
        assertThat(result.getResponse().getHeaders("TraceID"))
            .containsExactly(expectedTraceId);
    }

    /** 正常请求：Controller 内 MDC 持有本次 request-id，响应回写同值。 */
    @Test
    void normalRequest_controllerSeesMdcAndResponseHasHeader() throws Exception {
        mockMvc.perform(get("/test/ok").header("X-Request-Id", "req-1"))
            .andExpect(status().isOk())
            .andExpect(content().string("req-1"))
            .andExpect(result -> assertSingleCorrelation(result, "req-1", "req-1"));
    }

    /** 缺失 Header：生成 UUID，trace 回退 request。 */
    @Test
    void missingHeaders_generatesUuid() throws Exception {
        MvcResult result = mockMvc.perform(get("/test/ok"))
            .andExpect(status().isOk())
            .andReturn();
        String reqId = result.getResponse().getHeader("X-Request-Id");
        assertThat(reqId).isNotEmpty();
        // 缺失时仍单值
        assertThat(result.getResponse().getHeaders("X-Request-Id")).hasSize(1);
        assertThat(result.getResponse().getHeaders("TraceID")).containsExactly(reqId);
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
            .andExpect(result -> assertSingleCorrelation(result, "req-404", "req-404"));
    }

    /** Controller 抛异常：不重新选值，响应 Header 不变。 */
    @Test
    void controllerThrows_doesNotReselect() throws Exception {
        mockMvc.perform(get("/test/boom").header("X-Request-Id", "req-boom"))
            .andExpect(status().is5xxServerError())
            .andExpect(result -> assertSingleCorrelation(result, "req-boom", "req-boom"));
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
            .andExpect(result -> assertSingleCorrelation(result, "req-405", "req-405"));
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
            .andExpect(result -> assertSingleCorrelation(result, "req-401", "req-401"));
        // 认证 Filter 内 MDC 持有本次 request-id
        assertThat(mdcDuringAuth[0]).isEqualTo("req-401");
        // 退出后恢复入站前状态
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
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
            .andExpect(result -> assertSingleCorrelation(result, "req-400", "req-400"));
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
        MvcResult result = mockMvc.perform(
                get("/test/async").header("X-Request-Id", "req-async"))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.request()
                .asyncStarted())
            .andReturn();
        // 首次派发已写关联 Header（单值）
        assertThat(result.getResponse().getHeaders("X-Request-Id")).containsExactly("req-async");

        MvcResult asyncResult = mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                .asyncDispatch(result))
            .andExpect(status().isOk())
            .andExpect(content().string("async-result"))
            .andReturn();
        // ASYNC 再派发复用同值、不叠加（§11.3 + CD-013 单值）
        assertSingleCorrelation(asyncResult, "req-async", "req-async");

        // 异步完成后 MDC 恢复入站前状态
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    /**
     * SUT-01 CD-013：ControllerAdvice 经 builder 在 ResponseEntity 写 X-Request-Id（模拟
     * {@code ManagerHttpErrorResponseBuilder}），Spring 渲染时 {@code addHeader} 追加同值；
     * wrapper 在 Servlet 边界 {@code add→set}，保证 wire 单值。无 wrapper 时为两行同值。
     * §4.4 完整链 "ControllerAdvice 400 | body/header request ID 同值，Header 数量 1"。
     */
    @Test
    void controllerAdviceAddsCorrelationHeader_wireSingleValue() throws Exception {
        MockMvc mvc = MockMvcBuilders.standaloneSetup(new Cd013Controller())
            .addFilters(new CorrelationContextFilter())
            .setControllerAdvice(new Cd013Advice())
            .build();

        mvc.perform(get("/cd013/boom").header("X-Request-Id", "req-cd013"))
            .andExpect(status().isInternalServerError())
            .andExpect(result -> assertSingleCorrelation(result, "req-cd013", "req-cd013"))
            .andExpect(result -> {
                // body.request_id 与 Header 同值
                assertThat(result.getResponse().getContentAsString()).contains("req-cd013");
            });
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

    /** CD-013 复现：抛异常触发 builder-mimicking advice。 */
    @RestController
    @RequestMapping("/cd013")
    static class Cd013Controller {
        @GetMapping("/boom")
        public String boom() {
            throw new IllegalStateException("cd013-boom");
        }
    }

    /**
     * CD-013 复现：模拟 {@code ManagerHttpErrorResponseBuilder}——ResponseEntity 的
     * HttpHeaders 写 X-Request-Id（{@code headers.set("X-Request-Id", rid)}），body 也带
     * request_id。Spring 渲染该 ResponseEntity 时经 {@code addHeader} 追加到 Servlet
     * response，与 Filter 先写的 {@code setHeader} 叠加成两行；wrapper 把 add 转 set 保单值。
     */
    @org.springframework.web.bind.annotation.ControllerAdvice
    static class Cd013Advice {
        @org.springframework.web.bind.annotation.ExceptionHandler(IllegalStateException.class)
        public ResponseEntity<ErrorRsp> handle(IllegalStateException e) {
            String rid = MDC.get(MdcKeys.REQUEST_ID);
            ErrorRsp rsp = new ErrorRsp()
                .setErrorCode("openjiuwen.02001001")
                .setErrorMsg("boom")
                .setErrorReason("boom")
                .setErrorSuggestion("retry")
                .setRequestId(rid);
            HttpHeaders h = new HttpHeaders();
            h.setContentType(MediaType.APPLICATION_JSON);
            h.set("X-Request-Id", rid); // 模拟 ManagerHttpErrorResponseBuilder:59
            return new ResponseEntity<>(rsp, h, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}

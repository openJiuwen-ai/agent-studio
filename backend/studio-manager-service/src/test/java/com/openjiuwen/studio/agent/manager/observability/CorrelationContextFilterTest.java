/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.DispatcherType;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.ServletException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-05 §11：Manager 唯一 HTTP request/trace 选值、四 key 外层 scope、
 * 响应 Header 前置写入与 REQUEST/ASYNC/ERROR 派发生命周期测试。
 */
class CorrelationContextFilterTest {

    private final CorrelationContextFilter filter = new CorrelationContextFilter();

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    /** 捕获 chain 执行瞬间的 MDC 与响应 Header 可见性。 */
    private static final class CapturingChain implements FilterChain {
        final Map<String, String> mdcAtChain = new HashMap<>();
        String requestIdHeaderVisibleAtChain;

        @Override
        public void doFilter(ServletRequest req, ServletResponse res) {
            for (String key : MdcKeys.orderedKeys()) {
                mdcAtChain.put(key, MDC.get(key));
            }
            requestIdHeaderVisibleAtChain =
                ((org.springframework.mock.web.MockHttpServletResponse) res)
                    .getHeader(CorrelationContextFilter.REQUEST_ID_HEADER);
        }
    }

    private MockHttpServletRequest request(DispatcherType type) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setDispatcherType(type);
        return request;
    }

    // ---- §11.1 选值 ----

    @Test
    void validHeaders_selectedAndInstalled() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-123");
        request.addHeader(CorrelationContextFilter.TRACE_ID_HEADER, "trace-9");
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingChain chain = new CapturingChain();

        filter.doFilter(request, response, chain);

        assertThat(chain.mdcAtChain.get(MdcKeys.REQUEST_ID)).isEqualTo("req-123");
        assertThat(chain.mdcAtChain.get(MdcKeys.TRACE_ID)).isEqualTo("trace-9");
        assertThat(response.getHeader(CorrelationContextFilter.REQUEST_ID_HEADER)).isEqualTo("req-123");
        assertThat(response.getHeader(CorrelationContextFilter.TRACE_ID_HEADER)).isEqualTo("trace-9");
        // 结束后恢复入站前状态（未预置 → 移除）
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isNull();
    }

    @Test
    void missingHeaders_generatesUuidAndTraceFallsBackToRequest() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingChain chain = new CapturingChain();

        filter.doFilter(request, response, chain);

        String requestId = chain.mdcAtChain.get(MdcKeys.REQUEST_ID);
        assertThat(requestId).isNotEmpty();
        assertThat(CorrelationIdValidator.isValid(requestId)).isTrue();
        // trace 缺失回退 request_id
        assertThat(chain.mdcAtChain.get(MdcKeys.TRACE_ID)).isEqualTo(requestId);
        assertThat(response.getHeader(CorrelationContextFilter.REQUEST_ID_HEADER)).isEqualTo(requestId);
        assertThat(response.getHeader(CorrelationContextFilter.TRACE_ID_HEADER)).isEqualTo(requestId);
    }

    @Test
    void illegalHeaders_replacedByGenerated_notEchoed() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "bad value");
        request.addHeader(CorrelationContextFilter.TRACE_ID_HEADER, "tr@ce!");
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingChain chain = new CapturingChain();

        filter.doFilter(request, response, chain);

        String requestId = chain.mdcAtChain.get(MdcKeys.REQUEST_ID);
        assertThat(CorrelationIdValidator.isValid(requestId)).isTrue();
        // 非法原值不进 MDC、不回显到响应 Header
        assertThat(requestId).isNotEqualTo("bad value");
        assertThat(response.getHeader(CorrelationContextFilter.REQUEST_ID_HEADER)).isNotEqualTo("bad value");
        assertThat(response.getHeader(CorrelationContextFilter.TRACE_ID_HEADER)).isNotEqualTo("tr@ce!");
    }

    // ---- §11.4 响应 Header 前置写入 ----

    @Test
    void responseHeadersWrittenBeforeChainInvoke() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-early");
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingChain chain = new CapturingChain();

        filter.doFilter(request, response, chain);

        // chain 执行瞬间响应 Header 已可见（认证短路/404 也能携带同值的前提）
        assertThat(chain.requestIdHeaderVisibleAtChain).isEqualTo("req-early");
    }

    // ---- §11.2 四 key 外层 scope ----

    @Test
    void fourKeySweep_clearsHistoryAndRestoresOnExit() throws Exception {
        MDC.put(MdcKeys.REQUEST_ID, "old-request");
        MDC.put(MdcKeys.TRACE_ID, "old-trace");
        MDC.put(MdcKeys.EXECUTION_ID, "residue-exec");
        MDC.put(MdcKeys.CONVERSATION_ID, "residue-conv");
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-123");
        request.addHeader(CorrelationContextFilter.TRACE_ID_HEADER, "trace-9");
        CapturingChain chain = new CapturingChain();

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        // 业务代码视角：本请求 request/trace + 空 execution/conversation（清除容器线程残留）
        assertThat(chain.mdcAtChain.get(MdcKeys.REQUEST_ID)).isEqualTo("req-123");
        assertThat(chain.mdcAtChain.get(MdcKeys.TRACE_ID)).isEqualTo("trace-9");
        assertThat(chain.mdcAtChain.get(MdcKeys.EXECUTION_ID)).isEmpty();
        assertThat(chain.mdcAtChain.get(MdcKeys.CONVERSATION_ID)).isEmpty();
        // 退出后按入站前状态恢复四个 key
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("old-request");
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("old-trace");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("residue-exec");
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("residue-conv");
    }

    @Test
    void chainThrows_scopeClosedAndExceptionPropagates() {
        MDC.put(MdcKeys.REQUEST_ID, "old-request");
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-123");
        FilterChain throwingChain = (req, res) -> {
            throw new IllegalStateException("boom");
        };

        assertThatThrownBy(() -> filter.doFilter(request, new MockHttpServletResponse(), throwingChain))
            .isInstanceOf(IllegalStateException.class);
        // 异常路径同样关闭 scope，恢复入站前值
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("old-request");
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isNull();
    }

    // ---- §11.3 派发类型与复用 ----

    @Test
    void shouldNotFilterAsyncAndErrorDispatch_overriddenToFalse() throws Exception {
        // OncePerRequestFilter 默认两个 shouldNotFilter* 均为 true，必须显式覆盖
        java.lang.reflect.Method async =
            org.springframework.web.filter.OncePerRequestFilter.class.getDeclaredMethod("shouldNotFilterAsyncDispatch");
        async.setAccessible(true);
        java.lang.reflect.Method error =
            org.springframework.web.filter.OncePerRequestFilter.class.getDeclaredMethod("shouldNotFilterErrorDispatch");
        error.setAccessible(true);
        assertThat(async.invoke(filter)).isEqualTo(false);
        assertThat(error.invoke(filter)).isEqualTo(false);
    }

    @Test
    void independentErrorDispatch_reusesSelectedValues() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-first");
        CapturingChain first = new CapturingChain();
        filter.doFilter(request, new MockHttpServletResponse(), first);

        // 独立 ERROR 再派发：同一 request 对象（attribute 保留），工作线程已有残留
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");
        request.setDispatcherType(DispatcherType.ERROR);
        CapturingChain second = new CapturingChain();
        filter.doFilter(request, new MockHttpServletResponse(), second);

        // 复用首次选值：不生成第二组 ID，也不读工作线程残留
        assertThat(second.mdcAtChain.get(MdcKeys.REQUEST_ID)).isEqualTo("req-first");
        assertThat(second.mdcAtChain.get(MdcKeys.TRACE_ID)).isEqualTo("req-first");
        // 派发结束恢复残留值
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void asyncDispatch_reusesSelectedValues() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-first");
        CapturingChain first = new CapturingChain();
        filter.doFilter(request, new MockHttpServletResponse(), first);

        MDC.put(MdcKeys.TRACE_ID, "worker-residue");
        request.setDispatcherType(DispatcherType.ASYNC);
        CapturingChain second = new CapturingChain();
        filter.doFilter(request, new MockHttpServletResponse(), second);

        assertThat(second.mdcAtChain.get(MdcKeys.REQUEST_ID)).isEqualTo("req-first");
        assertThat(second.mdcAtChain.get(MdcKeys.TRACE_ID)).isEqualTo("req-first");
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("worker-residue");
    }

    // ---- §15.2.3 线程复用 ----

    @Test
    void threadReuse_secondRequestSeesNoFirstRequestIds() throws Exception {
        MockHttpServletRequest first = request(DispatcherType.REQUEST);
        first.addHeader(CorrelationContextFilter.REQUEST_ID_HEADER, "req-a");
        filter.doFilter(first, new MockHttpServletResponse(), new CapturingChain());

        // 线程复用：上一请求结束后其他组件遗留 execution/conversation 残留
        MDC.put(MdcKeys.EXECUTION_ID, "residue-exec");
        MDC.put(MdcKeys.CONVERSATION_ID, "residue-conv");
        MockHttpServletRequest second = request(DispatcherType.REQUEST);
        CapturingChain chain = new CapturingChain();
        filter.doFilter(second, new MockHttpServletResponse(), chain);

        String requestId = chain.mdcAtChain.get(MdcKeys.REQUEST_ID);
        // 第二请求生成自己的 ID，看不到第一请求的 req-a；残留被清场为空
        assertThat(CorrelationIdValidator.isValid(requestId)).isTrue();
        assertThat(requestId).isNotEqualTo("req-a");
        assertThat(chain.mdcAtChain.get(MdcKeys.EXECUTION_ID)).isEmpty();
        assertThat(chain.mdcAtChain.get(MdcKeys.CONVERSATION_ID)).isEmpty();
        // 结束后残留恢复
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("residue-exec");
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("residue-conv");
    }

    // ---- §15.2.5 / 审视 T4/B4：同线程嵌套 ERROR（doFilterNestedErrorDispatch） ----

    @Test
    void nestedErrorDispatch_hitsNestedBranch_mdcVisible_noDoubleScope() throws Exception {
        // 覆盖 doFilterNestedErrorDispatch + doFilterInternal 计数，证明真正命中嵌套分支
        final int[] doFilterInternalCount = {0};
        final int[] nestedErrorCount = {0};
        final String[] mdcDuringNested = {null};
        CorrelationContextFilter spy = new CorrelationContextFilter() {
            @Override
            protected void doFilterInternal(
                jakarta.servlet.http.HttpServletRequest req,
                jakarta.servlet.http.HttpServletResponse res,
                jakarta.servlet.FilterChain chain)
                throws jakarta.servlet.ServletException, java.io.IOException {
                doFilterInternalCount[0]++;
                super.doFilterInternal(req, res, chain);
            }

            @Override
            protected void doFilterNestedErrorDispatch(
                jakarta.servlet.http.HttpServletRequest req,
                jakarta.servlet.http.HttpServletResponse res,
                jakarta.servlet.FilterChain chain)
                throws jakarta.servlet.ServletException, java.io.IOException {
                nestedErrorCount[0]++;
                mdcDuringNested[0] = MDC.get(MdcKeys.REQUEST_ID);
                super.doFilterNestedErrorDispatch(req, res, chain);
            }
        };

        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        request.addHeader("X-Request-Id", "req-1");
        // chain 内部模拟同线程 response.sendError() 触发 ERROR 派发：
        // alreadyFilteredAttribute 仍在（REQUEST 派发 doFilterInternal 尚未返回）→ 命中嵌套分支
        jakarta.servlet.FilterChain chain = (req, res) -> {
            MockHttpServletRequest errorReq = (MockHttpServletRequest) req;
            errorReq.setDispatcherType(DispatcherType.ERROR);
            errorReq.setAttribute(jakarta.servlet.RequestDispatcher.ERROR_REQUEST_URI, "/test/ok");
            try {
                spy.doFilter(errorReq, res, (r2, r2res) -> { });
            } catch (Exception e) {
                throw new java.io.UncheckedIOException(new java.io.IOException(e));
            }
        };

        spy.doFilter(request, new MockHttpServletResponse(), chain);

        // REQUEST 进入 doFilterInternal（1 次）；嵌套 ERROR 命中 doFilterNestedErrorDispatch（1 次）
        assertThat(doFilterInternalCount[0]).isEqualTo(1);
        assertThat(nestedErrorCount[0]).isEqualTo(1);
        // 嵌套 ERROR 期间 REQUEST scope 仍有效（MDC 持有 request-id）
        assertThat(mdcDuringNested[0]).isEqualTo("req-1");
        // doFilterInternal 只被调用 1 次 → scope 不重复打开
        // 退出后恢复入站前状态
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.core.config.DefaultConfiguration;
import org.apache.logging.log4j.core.impl.Log4jLogEvent;
import org.apache.logging.log4j.core.layout.PatternLayout;
import org.apache.logging.log4j.message.SimpleMessage;
import org.apache.logging.log4j.util.SortedArrayStringMap;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.ErrorHandler;
import org.xml.sax.SAXParseException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.InputStream;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * VEC-01 §6.2 / 规划 §6.2：Manager Pattern 实际渲染测试——
 * 从 classpath 中真实 log4j2.xml 读出**已部署**的 LOG_PATTERN，直接构造 {@link PatternLayout}
 * 和 {@link Log4jLogEvent}（通过 context data 显式传入关联字段），不重启、不重配置全局
 * {@code LoggerContext}，不使用全局 MDC，避免污染其它用例。
 *
 * <p>用部署 pattern 而非常量：证明部署的 Pattern 不引用 {@code task-id}、不回退、空槽不左移；
 * 一旦有人把 LOG_PATTERN 改回 {@code %X{task-id}}，本测试立刻失败。
 */
class ManagerLogPatternRenderingTest {

    private static final String REQ = "req-1";
    private static final String EXEC = "exec-1";
    private static final String CONV = "conv-1";
    private static final String TRACE = "trace-1";
    private static final String TASK = "task-x";

    /** 从 classpath log4j2.xml 读出已部署的 LOG_PATTERN 属性值。 */
    private static String deployedPattern(String propName) throws Exception {
        try (InputStream in = ManagerLogPatternRenderingTest.class.getClassLoader()
            .getResourceAsStream("log4j2.xml")) {
            assertThat(in).as("log4j2.xml 须在 classpath").isNotNull();
            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            DocumentBuilder db = f.newDocumentBuilder();
            db.setErrorHandler(new FailErrorHandler());
            Document doc = db.parse(in);
            doc.getDocumentElement().normalize();
            NodeList props = doc.getElementsByTagName("Property");
            for (int i = 0; i < props.getLength(); i++) {
                Element el = (Element) props.item(i);
                if (propName.equals(el.getAttribute("name"))) {
                    String v = el.getAttribute("value");
                    return (v != null && !v.isEmpty()) ? v : el.getTextContent().trim();
                }
            }
            throw new IllegalStateException(propName + " 属性不存在");
        }
    }

    private PatternLayout layout(String pattern) throws Exception {
        return PatternLayout.newBuilder()
            .withConfiguration(new DefaultConfiguration())
            .withPattern(pattern)
            .build();
    }

    /** 用 {@link PatternLayout#toSerializable} 取字符串，避免默认字符集对中文/emoji 的影响。 */
    private String render(Log4jLogEvent event) throws Exception {
        return layout(deployedPattern("LOG_PATTERN")).toSerializable(event);
    }

    private String renderPerf(Log4jLogEvent event) throws Exception {
        return layout(deployedPattern("PERF_LOG_PATTERN")).toSerializable(event);
    }

    private Log4jLogEvent event(Map<String, String> mdc, String msg, Throwable thrown) {
        SortedArrayStringMap cd = new SortedArrayStringMap();
        if (mdc != null) {
            mdc.forEach(cd::putValue);
        }
        Log4jLogEvent.Builder b = Log4jLogEvent.newBuilder()
            .setLevel(Level.INFO)
            .setLoggerName("com.openjiuwen.studio.agent.manager.MockLogger")
            .setLoggerFqcn(getClass().getName())
            .setMessage(new SimpleMessage(msg))
            .setContextData(cd)
            .setTimeMillis(0L);
        if (thrown != null) {
            b.setThrown(thrown);
        }
        return b.build();
    }

    @Test
    void allCorrelationFieldsPresent_correctOrderAndValues() throws Exception {
        Log4jLogEvent e = event(Map.of("request-id", REQ, "execution-id", EXEC,
            "conversation-id", CONV, "trace_id", TRACE), "hello", null);
        String rendered = render(e);
        assertThat(rendered).contains("[" + REQ + "] [" + EXEC + "] [" + CONV + "] [" + TRACE + "]");
        assertThat(rendered).endsWith(" - [hello]" + System.lineSeparator());
    }

    @Test
    void executionMissing_emptySlotNoShift() throws Exception {
        Log4jLogEvent e = event(Map.of("request-id", REQ,
            "conversation-id", CONV, "trace_id", TRACE), "m", null);
        String rendered = render(e);
        assertThat(rendered).contains("[" + REQ + "] [] [" + CONV + "] [" + TRACE + "]");
    }

    @Test
    void allCorrelationMissing_fourEmptySlots() throws Exception {
        Log4jLogEvent e = event(Map.of(), "m", null);
        String rendered = render(e);
        assertThat(rendered).contains("[] [] [] []");
    }

    @Test
    void onlyTaskIdSet_executionSlotStaysEmpty() throws Exception {
        Log4jLogEvent e = event(Map.of("task-id", TASK), "m", null);
        String rendered = render(e);
        assertThat(rendered).contains("[] [] [] []");
        assertThat(rendered).doesNotContain(TASK);
    }

    @Test
    void taskIdAndExecutionIdSet_onlyExecutionRendered() throws Exception {
        Log4jLogEvent e = event(Map.of("task-id", TASK, "execution-id", EXEC), "m", null);
        String rendered = render(e);
        assertThat(rendered).contains("[] [" + EXEC + "] [] []");
        assertThat(rendered).doesNotContain(TASK);
    }

    @Test
    void unicodeAndBrackets_preserved() throws Exception {
        String msg = "中文测试 🎉 [bracket] pipe|bar 结束";
        Log4jLogEvent e = event(Map.of("request-id", REQ), msg, null);
        String rendered = render(e);
        assertThat(rendered).contains(msg);
        assertThat(rendered).endsWith(" - [" + msg + "]" + System.lineSeparator());
    }

    @Test
    void exceptionFirstLine_hasFixedOuterLayer_stackMultiLine() throws Exception {
        Throwable thrown = new IllegalStateException("boom");
        Log4jLogEvent e = event(Map.of(), "fail", thrown);
        String rendered = render(e);
        String firstLine = rendered.substring(0, rendered.indexOf(System.lineSeparator()));
        assertThat(firstLine).as("异常首行须含完整固定外层（四空槽）").contains("[] [] [] []");
        assertThat(firstLine).endsWith(" - [fail]");
        assertThat(rendered).as("异常类型与消息须出现").contains("java.lang.IllegalStateException: boom");
        assertThat(rendered).as("堆栈 continuation line 须存在").contains("\tat ");
    }

    // ---- Performance Pattern 实际渲染（代码审视 §3.2）----

    @Test
    void perfPattern_rendersLevelAndCorrelation_noThreadOrLoggerLine() throws Exception {
        Log4jLogEvent e = event(Map.of("request-id", REQ, "execution-id", EXEC,
            "conversation-id", CONV, "trace_id", TRACE), "perf", null);
        String rendered = renderPerf(e);
        assertThat(rendered).contains("[INFO ] [" + REQ + "] [" + EXEC + "] [" + CONV + "] [" + TRACE + "] - [perf]");
        // performance 不含 thread/logger:line — trace 槽后直接是 " - [msg]"，无 [thread] 段
        assertThat(rendered).contains("[" + TRACE + "] - [perf]");
        assertThat(rendered).doesNotContain(MockLoggerLineMarker.FILE_LINE_MARKER);
        assertThat(rendered).endsWith(" - [perf]" + System.lineSeparator());
    }

    @Test
    void perfPattern_emptySlotsPreserved() throws Exception {
        Log4jLogEvent e = event(Map.of(), "m", null);
        String rendered = renderPerf(e);
        assertThat(rendered).contains("[] [] [] [] - [m]");
    }

    private static final class MockLoggerLineMarker {
        /** logger 名含冒号行号特征：main 布局会渲染为 [logger:line]，performance 不应出现该段。 */
        static final String FILE_LINE_MARKER = "MockLogger:";
    }

    private static final class FailErrorHandler implements ErrorHandler {
        @Override public void warning(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void error(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void fatalError(SAXParseException e) { throw new RuntimeException(e); }
    }
}

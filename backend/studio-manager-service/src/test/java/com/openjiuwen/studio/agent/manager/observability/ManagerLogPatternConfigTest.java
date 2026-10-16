/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.core.Appender;
import org.apache.logging.log4j.core.LoggerContext;
import org.apache.logging.log4j.core.config.ConfigurationSource;
import org.apache.logging.log4j.core.config.xml.XmlConfiguration;
import org.apache.logging.log4j.status.StatusData;
import org.apache.logging.log4j.status.StatusListener;
import org.apache.logging.log4j.status.StatusLogger;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.ErrorHandler;
import org.xml.sax.SAXParseException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * VEC-01 §6.1 / 规划 §6.1：Manager log4j2.xml 配置结构测试——
 * 解析 classpath 中真实 log4j2.xml，断言：
 * <ul>
 *   <li>LOG_PATTERN 与 VEC-01 §3.1 冻结串逐字符一致；</li>
 *   <li>PERF_LOG_PATTERN 与 §3.2 冻结串逐字符一致；</li>
 *   <li>TRACE_LOG_PATTERN 仍为 {@code %msg%n}；</li>
 *   <li>XML 中不存在 {@code %X{task-id}}；</li>
 *   <li>main 与 Console 引用 LOG_PATTERN；performance 引用 PERF_LOG_PATTERN；audit 引用 TRACE_LOG_PATTERN；</li>
 *   <li>历史 interface Pattern/appender/async appender 及专用轮转属性均已删除；</li>
 *   <li>所有 AppenderRef 的目标都能解析到同名 appender，不存在 dangling reference。</li>
 * </ul>
 * 不用源码字符串搜索代替 XML 解析；raw 字符串扫描仅作附加门禁。
 */
class ManagerLogPatternConfigTest {

    static final String LOG_PATTERN =
        "[%d{yyyy-MM-dd HH:mm:ss.SSS}] [%-5level] [%X{request-id}] [%X{execution-id}] [%X{conversation-id}] [%X{trace_id}] [%thread] [%logger{15}:%L] - [%msg]%n";

    static final String PERF_LOG_PATTERN =
        "[%d{yyyy-MM-dd HH:mm:ss.SSS}] [%-5level] [%X{request-id}] [%X{execution-id}] [%X{conversation-id}] [%X{trace_id}] - [%msg]%n";

    static final String TRACE_LOG_PATTERN = "%msg%n";

    private static final Set<String> APPENDER_TAGS = Set.of("Console", "RollingFile", "Async");

    private Document loadXml() throws Exception {
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("log4j2.xml")) {
            assertThat(in).as("log4j2.xml 须在 classpath").isNotNull();
            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            f.setNamespaceAware(false);
            DocumentBuilder db = f.newDocumentBuilder();
            db.setErrorHandler(new FailErrorHandler());
            Document doc = db.parse(in);
            doc.getDocumentElement().normalize();
            return doc;
        }
    }

    private String rawXml() throws Exception {
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("log4j2.xml")) {
            assertThat(in).as("log4j2.xml 须在 classpath").isNotNull();
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private String property(Document doc, String name) {
        NodeList props = doc.getElementsByTagName("Property");
        for (int i = 0; i < props.getLength(); i++) {
            Element el = (Element) props.item(i);
            if (!name.equals(el.getAttribute("name"))) {
                continue;
            }
            String v = el.getAttribute("value");
            return (v != null && !v.isEmpty()) ? v : el.getTextContent().trim();
        }
        return null;
    }

    private Element appender(Document doc, String name) {
        for (String tag : APPENDER_TAGS) {
            NodeList list = doc.getElementsByTagName(tag);
            for (int i = 0; i < list.getLength(); i++) {
                Element el = (Element) list.item(i);
                if (name.equals(el.getAttribute("name"))) {
                    return el;
                }
            }
        }
        return null;
    }

    private String appenderPattern(Document doc, String appenderName) {
        Element app = appender(doc, appenderName);
        if (app == null) {
            return null;
        }
        NodeList layouts = app.getElementsByTagName("PatternLayout");
        if (layouts.getLength() == 0) {
            return null;
        }
        return ((Element) layouts.item(0)).getAttribute("pattern");
    }

    private Set<String> allAppenderNames(Document doc) {
        Set<String> names = new LinkedHashSet<>();
        for (String tag : APPENDER_TAGS) {
            NodeList list = doc.getElementsByTagName(tag);
            for (int i = 0; i < list.getLength(); i++) {
                String n = ((Element) list.item(i)).getAttribute("name");
                if (n != null && !n.isEmpty()) {
                    names.add(n);
                }
            }
        }
        return names;
    }

    private Set<String> allAppenderRefTargets(Document doc) {
        Set<String> refs = new LinkedHashSet<>();
        NodeList list = doc.getElementsByTagName("AppenderRef");
        for (int i = 0; i < list.getLength(); i++) {
            String ref = ((Element) list.item(i)).getAttribute("ref");
            if (ref != null && !ref.isEmpty()) {
                refs.add(ref);
            }
        }
        return refs;
    }

    @Test
    void logPattern_matchesFrozenContract() throws Exception {
        assertThat(property(loadXml(), "LOG_PATTERN")).isEqualTo(LOG_PATTERN);
    }

    @Test
    void perfLogPattern_matchesFrozenContract() throws Exception {
        assertThat(property(loadXml(), "PERF_LOG_PATTERN")).isEqualTo(PERF_LOG_PATTERN);
    }

    @Test
    void traceLogPattern_remainsMsgOnly() throws Exception {
        assertThat(property(loadXml(), "TRACE_LOG_PATTERN")).isEqualTo(TRACE_LOG_PATTERN);
    }

    @Test
    void noTaskIdAnywhere() throws Exception {
        String raw = rawXml();
        assertThat(raw).doesNotContain("%X{task-id}");
    }

    @Test
    void mainAndConsoleReferenceLogPattern() throws Exception {
        Document doc = loadXml();
        assertThat(appenderPattern(doc, "STDOUT")).isEqualTo("${LOG_PATTERN}");
        assertThat(appenderPattern(doc, "ROLLING_FILE")).isEqualTo("${LOG_PATTERN}");
    }

    @Test
    void performanceAppenderReferencesPerfPattern() throws Exception {
        assertThat(appenderPattern(loadXml(), "ROLLING_FILE_PERFORM")).isEqualTo("${PERF_LOG_PATTERN}");
    }

    @Test
    void auditAppenderReferencesTracePattern() throws Exception {
        assertThat(appenderPattern(loadXml(), "ROLLING_FILE_TRACE")).isEqualTo("${TRACE_LOG_PATTERN}");
    }

    @Test
    void interfaceConfigDeleted() throws Exception {
        Document doc = loadXml();
        assertThat(property(doc, "INF_LOG_PATTERN")).as("INF_LOG_PATTERN 须删除").isNull();
        assertThat(property(doc, "INF_FILE_ROLLING_SIZE")).isNull();
        assertThat(property(doc, "INF_FILE_MAX_COUNT")).isNull();
        assertThat(property(doc, "INF_FILE_MAX_AGE")).isNull();
        assertThat(property(doc, "INF_FILE_MAX_TOTAL_SIZE")).isNull();
        assertThat(property(doc, "INF_FILE_MAX_TOTAL_COUNT")).isNull();
        assertThat(appender(doc, "ROLLING_FILE_INF")).as("ROLLING_FILE_INF 须删除").isNull();
        assertThat(appender(doc, "ASYNC_ROLLING_FILE_INF")).as("ASYNC_ROLLING_FILE_INF 须删除").isNull();
        assertThat(rawXml()).doesNotContain("interface.log");
    }

    @Test
    void noDanglingAppenderReferences() throws Exception {
        Document doc = loadXml();
        Set<String> names = allAppenderNames(doc);
        Set<String> refs = allAppenderRefTargets(doc);
        assertThat(refs).as("所有 AppenderRef 目标须存在同名 appender").isSubsetOf(names);
    }

    /**
     * VEC-01 §6.1 / 代码审视 §3.1：用真实 Log4j2 加载 classpath 中的 log4j2.xml。
     * DOM 解析只能证明 XML 语法正确；本测试证明 Log4j2 Core 自身识别全部 appender/plugin、
     * 无 unknown appender、无 dangling reference 或无效属性配置错误。
     *
     * <p>使用独立 {@link LoggerContext}（非全局 LogManager 全局上下文），不重配置全局 LoggerContext；
     * 加载前把生产日志根路径 {@code /opt/cloud/studio-manager/logs} 重定向到 JUnit {@code @TempDir}，
     * 避免真实 RollingFile/Async appender 打开或创建生产日志文件（代码审视 §3.1 文件路径副作用）；
     * 其余 Pattern、appender 名、引用与结构断言保持不变，确保只改写入路径不掩盖生产配置结构问题。
     * 加载期间注册临时 {@link StatusListener} 捕获 ERROR/FATAL 状态，结束即移除并终止独立上下文。
     */
    @Test
    void log4j2_loadsConfigWithoutErrors(@TempDir Path tempDir) throws Exception {
        List<String> errors = new ArrayList<>();
        StatusListener listener = new StatusListener() {
            @Override public void log(StatusData data) {
                if (data.getLevel() == Level.ERROR || data.getLevel() == Level.FATAL) {
                    errors.add(data.getLevel() + ": " + data.getMessage().getFormattedMessage());
                }
            }
            @Override public Level getStatusLevel() { return Level.ERROR; }
            @Override public void close() { /* no-op */ }
        };
        StatusLogger.getLogger().registerListener(listener);
        LoggerContext ctx = new LoggerContext("vec01-config-load-test");
        try {
            String text = rawXml();
            String redirected = text.replace("/opt/cloud/studio-manager/logs", tempDir.toString());
            assertThat(redirected).as("生产日志路径须被重定向到临时目录").doesNotContain("/opt/cloud/studio-manager/logs");
            XmlConfiguration xmlConfig = new XmlConfiguration(ctx,
                new ConfigurationSource(new ByteArrayInputStream(redirected.getBytes(StandardCharsets.UTF_8))));
            ctx.start(xmlConfig);
            assertThat(ctx.isStarted()).as("独立 LoggerContext 须成功启动").isTrue();
            Map<String, Appender> appenders = ctx.getConfiguration().getAppenders();
            assertThat(appenders.keySet()).as("Log4j2 须识别全部目标 appender")
                .contains("STDOUT", "ROLLING_FILE", "ROLLING_FILE_PERFORM", "ROLLING_FILE_TRACE",
                    "ASYNC_STDOUT", "ASYNC_ROLLING_FILE", "ASYNC_ROLLING_FILE_PERFORM",
                    "ASYNC_ROLLING_FILE_TRACE");
            assertThat(appenders.keySet()).as("历史 interface appender 不得被识别")
                .doesNotContain("ROLLING_FILE_INF", "ASYNC_ROLLING_FILE_INF");
        } finally {
            ctx.terminate();
            StatusLogger.getLogger().removeListener(listener);
        }
        assertThat(errors).as("Log4j2 加载 log4j2.xml 须无 ERROR/FATAL 状态: %s", errors).isEmpty();
    }

    private static final class FailErrorHandler implements ErrorHandler {
        @Override public void warning(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void error(SAXParseException e) { throw new RuntimeException(e); }
        @Override public void fatalError(SAXParseException e) { throw new RuntimeException(e); }
    }
}

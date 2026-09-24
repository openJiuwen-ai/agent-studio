/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.manager.observability.OutboundCorrelationPolicy;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Runtime Feign 方法级出站策略清单（COM-04 §6.1/§10.4）。
 *
 * <p>权威分类按方法名显式维护；路径模板经反射从 {@link AgentRuntimeClient} 的
 * mapping 注解读取并编译为匹配正则，供拦截器在运行期按（HTTP 方法 + 已解析路径）
 * 解析策略。新增方法未登记时由治理测试失败；运行期未匹配路径按编程错误抛出，
 * 不得默认无 Header 或默认执行。
 *
 * <p>分类依据（§6.1）：Agent/Workflow/网页执行/节点执行为 RUNTIME_EXECUTION；
 * 查询、管理、代理 Tool/MCP、任务注册（createTask 无生产调用方且 Runtime 侧仅
 * 落异步任务定义）等其余方法为 RUNTIME_NON_EXECUTION。方法名含 run/call 不构成
 * 执行分类依据（runTool/callMcpServerTool 为反例）。
 */
public final class AgentRuntimeFeignMethodCatalog {

    /** 执行调用（7）：Agent/Workflow 执行 ×4、节点执行、网页 Workflow/Agent。 */
    private static final Map<String, OutboundCorrelationPolicy> METHOD_POLICIES = buildPolicies();

    private static Map<String, OutboundCorrelationPolicy> buildPolicies() {
        Map<String, OutboundCorrelationPolicy> map = new LinkedHashMap<>();
        // ---- RUNTIME_EXECUTION（§6.1 显式清单）----
        map.put("runAgentWithConversation", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runAgentWithConversationStream", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runWorkflowWithConversation", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runWorkflowWithConversationStream", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runWorkflowNodeExecute", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runWebWorkflow", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        map.put("runWebAgent", OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        // ---- RUNTIME_NON_EXECUTION（其余全部方法，逐项显式登记）----
        map.put("createReleaseInfo", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("deleteReleaseInfo", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("uploadAgentFile", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("resetConversationMemory", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("retrieveConversationMemory", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        // sync_01 新业务记忆管理（updateMemory/clearUserMemories）——非执行
        map.put("updateMemory", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("clearUserMemories", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("listIndustry", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        // Runtime 侧仅注册异步任务定义（对应 Manager 自身 createTask 只落库），
        // 且无生产调用方——非执行；若后续调用链变化须重新评审并更新本清单与测试。
        map.put("createTask", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("testServer", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("additionalQuestions", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("additionalQuestionsWorkflow", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("runTool", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("textToSpeech", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("audioTranscriptions", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("analyticsEvent", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("voiceRecognition", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("abortConversation", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("clearResourceCache", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("deleteMemoryRepoData", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("listMemories", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("batchDeleteMemories", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("searchMemories", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("createOpenJiuwenKB", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("uploadOpenJiuwenKBFile", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("searchOpenJiuwenKB", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("deleteOpenJiuwenKB", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        // sync_01 新业务：删除 KB 文档——非执行
        map.put("deleteOpenJiuwenKBDocument", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        map.put("listOpenJiuwenKBs", OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        return Collections.unmodifiableMap(map);
    }

    /** （HTTP 方法 + 路径模板）→ 编译正则，按方法名构建。 */
    private static final List<RouteRule> ROUTE_RULES = buildRules();

    private static final class RouteRule {
        final String httpMethod;
        final Pattern pathPattern;
        final OutboundCorrelationPolicy policy;

        RouteRule(String httpMethod, Pattern pathPattern, OutboundCorrelationPolicy policy) {
            this.httpMethod = httpMethod;
            this.pathPattern = pathPattern;
            this.policy = policy;
        }
    }

    private static List<RouteRule> buildRules() {
        List<RouteRule> rules = new ArrayList<>();
        for (Method method : AgentRuntimeClient.class.getDeclaredMethods()) {
            OutboundCorrelationPolicy policy = METHOD_POLICIES.get(method.getName());
            if (policy == null) {
                continue; // 治理测试负责暴露未登记方法
            }
            String[] mapping = readMapping(method);
            if (mapping == null) {
                continue;
            }
            rules.add(new RouteRule(mapping[0], compile(mapping[1]), policy));
        }
        return Collections.unmodifiableList(rules);
    }

    /** 读取方法 mapping 注解，返回 [httpMethod, pathTemplate]；无 mapping 返回 null。 */
    static String[] readMapping(Method method) {
        PostMapping post = method.getAnnotation(PostMapping.class);
        if (post != null) {
            return new String[] {"POST", firstPath(post.path().length > 0 ? post.path() : post.value())};
        }
        GetMapping get = method.getAnnotation(GetMapping.class);
        if (get != null) {
            return new String[] {"GET", firstPath(get.path().length > 0 ? get.path() : get.value())};
        }
        DeleteMapping delete = method.getAnnotation(DeleteMapping.class);
        if (delete != null) {
            return new String[] {"DELETE", firstPath(delete.path().length > 0 ? delete.path() : delete.value())};
        }
        PutMapping put = method.getAnnotation(PutMapping.class);
        if (put != null) {
            return new String[] {"PUT", firstPath(put.path().length > 0 ? put.path() : put.value())};
        }
        RequestMapping request = method.getAnnotation(RequestMapping.class);
        if (request != null) {
            String httpMethod = request.method().length > 0 ? request.method()[0].name() : "GET";
            return new String[] {httpMethod, firstPath(request.path().length > 0 ? request.path()
                : request.value())};
        }
        return null;
    }

    private static String firstPath(String[] paths) {
        return paths.length > 0 ? paths[0] : "/";
    }

    /** 路径模板编译：{var} → [^/]+，整串匹配。 */
    static Pattern compile(String pathTemplate) {
        String regex = pathTemplate.replaceAll("\\{[^/]+?}", "[^/]+");
        return Pattern.compile("^" + regex + "$");
    }

    private AgentRuntimeFeignMethodCatalog() {
    }

    /** 方法名 → 权威策略（治理测试对账用）。 */
    public static Map<String, OutboundCorrelationPolicy> methodPolicies() {
        return METHOD_POLICIES;
    }

    /**
     * 运行期解析（已解析路径，不含 query）。
     *
     * @throws IllegalStateException 未匹配任何登记路由——视为清单治理错误，调用失败
     */
    public static OutboundCorrelationPolicy resolve(String httpMethod, String resolvedPath) {
        String path = resolvedPath == null ? "" : resolvedPath;
        int query = path.indexOf('?');
        if (query >= 0) {
            path = path.substring(0, query);
        }
        for (RouteRule rule : ROUTE_RULES) {
            if (rule.httpMethod.equalsIgnoreCase(httpMethod) && rule.pathPattern.matcher(path).matches()) {
                return rule.policy;
            }
        }
        throw new IllegalStateException("unclassified Runtime Feign call: " + httpMethod + " " + path);
    }
}

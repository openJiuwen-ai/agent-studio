/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Set;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.context.annotation.ClassPathScanningCandidateComponentProvider;
import org.springframework.core.annotation.AnnotatedElementUtils;
import org.springframework.core.type.filter.AnnotationTypeFilter;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-05 §15.3.5：路由清单对账——扫描 manager 全部 @RestController，
 * 每个含 {conversation_id} 或 {cid} 路径变量的 MVC 路由必须已绑定校验 profile；
 * 注册表中的路由也必须真实存在（防陈旧项）。Feign 出站声明不属于 MVC，不计入。
 */
class ConversationRouteRegistryTest {

    /** 扫描 manager 包下全部 @RestController 的会话路由并与注册表对账。 */
    @Test
    void everyConversationRouteIsRegisteredAndNoStaleEntries() throws Exception {
        Set<String> controllerRoutes = scanConversationRoutes();
        Set<String> registered = ConversationIdValidator.registeredPatterns();

        // 新增会话路由未登记 → 失败（防遗漏）
        assertThat(controllerRoutes).isNotEmpty();
        assertThat(registered).containsAll(controllerRoutes);
        // 注册表陈旧项（路由已删除）→ 失败（防漂移）
        assertThat(controllerRoutes).containsAll(registered);
    }

    /** 每个会话参数的 Controller 注解必须与注册 profile 共享同一常量（防两份规则漂移）。 */
    @Test
    void everyConversationParamAnnotationMatchesRegisteredProfile() throws Exception {
        ClassPathScanningCandidateComponentProvider scanner =
            new ClassPathScanningCandidateComponentProvider(false);
        scanner.addIncludeFilter(new AnnotationTypeFilter(RestController.class));

        int checked = 0;
        for (BeanDefinition bd : scanner.findCandidateComponents("com.openjiuwen.studio.agent.manager.controller")) {
            Class<?> clazz = Class.forName(bd.getBeanClassName());
            // §15.3.5：Feign 出站声明（接口/非 @RestController）不得计入入口清单
            if (clazz.isInterface() || !isMvcController(clazz)) {
                continue;
            }
            for (Method method : clazz.getDeclaredMethods()) {
                for (int i = 0; i < method.getParameters().length; i++) {
                    java.lang.reflect.Parameter param = method.getParameters()[i];
                    // api 模块接口实现的参数注解在接口方法上——类内参数无注解时回退到接口方法参数
                    java.lang.reflect.Parameter effective = hasAnnotations(param)
                        ? param : interfaceParameter(clazz, method, i);
                    if (effective == null) {
                        continue;
                    }
                    PathVariable pv = effective.getAnnotation(PathVariable.class);
                    if (pv == null) {
                        continue;
                    }
                    String name = pv.value().isEmpty() ? effective.getName() : pv.value();
                    if (!"conversation_id".equals(name) && !"cid".equals(name)) {
                        continue;
                    }
                    String route = routeOf(method, clazz);
                    ConversationIdValidator.Profile profile = ConversationIdValidator.profileFor(route);
                    assertThat(profile).as("route %s 未登记 profile", route + " @" + clazz.getName()).isNotNull();
                    jakarta.validation.constraints.Pattern pattern =
                        effective.getAnnotation(jakarta.validation.constraints.Pattern.class);
                    assertThat(pattern).as("route %s 的 %s 参数缺少 @Pattern", route, name).isNotNull();
                    assertThat(pattern.regexp()).as("route %s 的注解与 profile 常量漂移", route)
                        .isEqualTo(expectedRegexp(profile));
                    checked++;
                }
            }
        }
        // AgentServiceProxyController 16 个 conversation_id（feedback 两方法）
        // + ConversationHistoryApiController history ×2 + WorkflowRuntimeApiController ×1 + N2L cid ×1
        assertThat(checked).isEqualTo(20);
    }

    private boolean hasAnnotations(java.lang.reflect.Parameter param) {
        return param.getAnnotations().length > 0;
    }

    /** 控制器实现接口且自身参数无注解时，取接口方法同位置参数（约束声明在接口上的既有模式）。 */
    private java.lang.reflect.Parameter interfaceParameter(Class<?> clazz, Method method, int index) {
        for (Class<?> iface : clazz.getInterfaces()) {
            for (Method im : iface.getMethods()) {
                if (im.getName().equals(method.getName())
                    && im.getParameterCount() == method.getParameterCount()) {
                    return im.getParameters()[index];
                }
            }
        }
        return null;
    }

    private boolean isMvcController(Class<?> clazz) {
        return AnnotatedElementUtils.findMergedAnnotation(clazz, RestController.class) != null
            || AnnotatedElementUtils.findMergedAnnotation(clazz, org.springframework.stereotype.Controller.class) != null;
    }

    private String expectedRegexp(ConversationIdValidator.Profile profile) {
        return switch (profile) {
            case STANDARD_CONVERSATION -> ConversationIdValidator.STANDARD_CONVERSATION_REGEXP;
            case WORKFLOW_CONVERSATION -> ConversationIdValidator.WORKFLOW_CONVERSATION_REGEXP;
            case N2L_CONVERSATION -> ConversationIdValidator.N2L_CONVERSATION_REGEXP;
        };
    }

    private String routeOf(Method method, Class<?> clazz) {
        RequestMapping classMapping = AnnotatedElementUtils.findMergedAnnotation(clazz, RequestMapping.class);
        String[] prefixes = classMapping != null ? classMapping.path() : new String[0];
        RequestMapping mapping = AnnotatedElementUtils.findMergedAnnotation(method, RequestMapping.class);
        if (mapping == null || mapping.path().length == 0) {
            return "?";
        }
        String prefix = prefixes.length > 0 ? prefixes[0] : "";
        return (prefix + mapping.path()[0]).replaceFirst("^/", "/");
    }

    private Set<String> scanConversationRoutes() throws Exception {
        ClassPathScanningCandidateComponentProvider scanner =
            new ClassPathScanningCandidateComponentProvider(false);
        scanner.addIncludeFilter(new AnnotationTypeFilter(RestController.class));

        Set<String> routes = new HashSet<>();
        for (BeanDefinition bd : scanner.findCandidateComponents("com.openjiuwen.studio.agent.manager.controller")) {
            Class<?> clazz = Class.forName(bd.getBeanClassName());
            if (clazz.isInterface() || !isMvcController(clazz)) {
                continue;
            }
            RequestMapping classMapping =
                AnnotatedElementUtils.findMergedAnnotation(clazz, RequestMapping.class);
            String[] prefixes = classMapping != null ? classMapping.path() : new String[0];
            for (Method method : clazz.getDeclaredMethods()) {
                RequestMapping mapping =
                    AnnotatedElementUtils.findMergedAnnotation(method, RequestMapping.class);
                if (mapping == null) {
                    continue;
                }
                for (String pattern : mapping.path()) {
                    for (String prefix : prefixes.length > 0 ? prefixes : new String[] {""}) {
                        String full = (prefix + pattern).replaceFirst("^/", "/");
                        if (full.contains("{conversation_id}") || full.contains("{cid}")) {
                            routes.add(full);
                        }
                    }
                }
            }
        }
        return routes;
    }
}

package com.openjiuwen.studio.conversation.infrastructure.adapter;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.source.ConfigurationPropertySources;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.PropertySource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.mock.env.MockEnvironment;

import java.io.IOException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 诊断 conversation adapter 的 @Value 键与 application-manager.yml 的匹配关系。
 *
 * <p>模拟 Spring Boot 属性解析路径（加载 yml + ConfigurationPropertySources relaxed binding），
 * 一次打印三组解析结果做对照：</p>
 * <ol>
 *   <li>控制项：${conversation-workspace.team-agent-ids:}（kebab 嵌套键，精确匹配）——用于验证 harness 忠实</li>
 *   <li>adapter 当前读法：${agent_runtime_endpoint:}（平铺下划线键）</li>
 *   <li>yml 嵌套键：${agent-runtime.endpoint:}（kebab 嵌套键）</li>
 * </ol>
 */
class AgentRuntimeConfigTest {

    @Test
    void testYml_ConfigKeyMatching() throws IOException {
        YamlPropertySourceLoader loader = new YamlPropertySourceLoader();
        List<PropertySource<?>> sources = loader.load("app-manager",
                new ClassPathResource("application-manager.yml"));

        MockEnvironment env = new MockEnvironment();
        sources.forEach(env.getPropertySources()::addFirst);
        ConfigurationPropertySources.attach(env);

        // ① 控制项：kebab 嵌套键精确匹配，应解析出 UUID → 证明 harness 忠实于 Spring 行为
        String teamAgentIds = env.resolvePlaceholders("${conversation-workspace.team-agent-ids:}");
        System.out.println(">> [控制] conversation-workspace.team-agent-ids = [" + teamAgentIds + "]");
        assertFalse(teamAgentIds.isEmpty(), "控制项失败：harness 未忠实模拟 Spring，后续结论不可信");

        // ② adapter 当前读的平铺键（无 inner 前缀，对不上任何 yml 键）
        String flat = env.resolvePlaceholders("${agent_runtime_endpoint:}");
        System.out.println(">> ${agent_runtime_endpoint:}（adapter 当前读法） = [" + flat + "]");

        // ③ yml 里真实存在的键：inner.agent-runtime.endpoint（带 inner 前缀，中划线）
        String correct = env.resolvePlaceholders("${inner.agent-runtime.endpoint:}");
        System.out.println(">> ${inner.agent-runtime.endpoint:}（中划线，已验证） = [" + correct + "]");

        // ④ 用户实际写的形式：inner.agent_runtime.endpoint（下划线）——是否 relaxed binding 能匹配？
        String underscore = env.resolvePlaceholders("${inner.agent_runtime.endpoint:}");
        System.out.println(">> ${inner.agent_runtime.endpoint:}（下划线，用户写的） = [" + underscore + "]");
    }
}

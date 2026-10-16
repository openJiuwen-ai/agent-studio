/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;

/**
 * FeignClientRegistry 全量治理测试（COM-04 §5.2/§10.4，兑现 registry 注释承诺）。
 *
 * <p>扫描 studio-manager-service + studio-common 全部 main 源码的 {@code @FeignClient}，
 * 双向断言：① 每个客户端 name 已在 {@link FeignClientRegistry} 显式分类；② registry 无陈旧条目。
 *
 * <p>另守卫 followRedirects 的 yml 命名空间：openfeign 4.x 只绑定
 * {@code spring.cloud.openfeign.client.config.<name>}（FeignClientProperties 前缀），
 * 顶层 {@code feign.client.config.*} 是死命名空间——落错树不生效（adversarial 第 4 轮 ADV4-1
 * 曾漏过）。断言允许的两个客户端在正确命名空间显式 {@code followRedirects: false}，
 * 且死命名空间不残留该键。
 */
class FeignClientRegistryCoverageTest {

    private static final Pattern BLOCK_COMMENT = Pattern.compile("/\\*.*?\\*/", Pattern.DOTALL);
    // 仅剥行首 // 注释：字符串字面量内的 //（如 url = "http://..."）不得被截断——
    // 否则 @FeignClient 注解被腰斩，name 位于其后时静默漏收（ADV5-1 latent 通道）
    private static final Pattern LINE_COMMENT = Pattern.compile("^[ \\t]*//[^\\n]*", Pattern.MULTILINE);
    private static final Pattern FEIGN_CLIENT = Pattern.compile("@FeignClient\\s*\\((.*?)\\)", Pattern.DOTALL);
    private static final Pattern NAME_ATTR = Pattern.compile("(?:name|value)\\s*=\\s*\"([^\"]+)\"");
    private static final Pattern BARE_VALUE = Pattern.compile("^\\s*\"([^\"]+)\"");

    private static List<Path> sourceRoots() {
        List<Path> roots = new ArrayList<>();
        roots.add(Paths.get("src/main/java"));
        // fail-fast：common 根不可达时静默跳过会让 studio-common 的 iamManager/modelManager
        // 脱离治理仍全绿（治理范围静默收窄）——必须响亮失败而非降级
        Path common = Paths.get("../studio-common/src/main/java");
        assertThat(Files.isDirectory(common))
            .as("studio-common 源码根不可达（working dir 漂移？）——治理测试不得静默收窄扫描范围")
            .isTrue();
        roots.add(common);
        return roots;
    }

    private static List<String> scanFeignClientNames() throws IOException {
        TreeSet<String> names = new TreeSet<>();
        for (Path root : sourceRoots()) {
            try (Stream<Path> files = Files.walk(root)) {
                for (Path p : files.filter(f -> f.toString().endsWith(".java")).toList()) {
                    String src = Files.readString(p, StandardCharsets.UTF_8);
                    String noComment = LINE_COMMENT.matcher(
                        BLOCK_COMMENT.matcher(src).replaceAll("")).replaceAll("");
                    Matcher m = FEIGN_CLIENT.matcher(noComment);
                    while (m.find()) {
                        String args = m.group(1);
                        Matcher nm = NAME_ATTR.matcher(args);
                        if (nm.find()) {
                            names.add(nm.group(1));
                        } else {
                            Matcher bv = BARE_VALUE.matcher(args);
                            if (bv.find()) {
                                names.add(bv.group(1));
                            }
                        }
                    }
                }
            }
        }
        return new ArrayList<>(names);
    }

    @Test
    void every_feign_client_is_classified() throws IOException {
        List<String> unclassified = new ArrayList<>();
        for (String name : scanFeignClientNames()) {
            if (FeignClientRegistry.decisionFor(name) == FeignClientRegistry.Decision.UNCLASSIFIED) {
                unclassified.add(name);
            }
        }
        assertThat(unclassified)
            .as("存在未在 FeignClientRegistry.DECISIONS 登记的 @FeignClient（未登记客户端绕过目标归属评审；新增客户端须显式分类为 RUNTIME/BUILDER/DENY）")
            .isEmpty();
    }

    @Test
    void no_stale_entries_in_registry() throws IOException {
        List<String> found = scanFeignClientNames();
        List<String> stale = new ArrayList<>();
        for (String name : new TreeSet<>(FeignClientRegistry.allClassifiedClients())) {
            if (!found.contains(name)) {
                stale.add(name);
            }
        }
        assertThat(stale)
            .as("FeignClientRegistry 中存在源码已不存在的陈旧客户端条目（客户端已删除，registry 未同步）")
            .isEmpty();
    }

    /** openfeign 4.x 绑定命名空间守卫：followRedirects 必须在 spring.cloud.openfeign.client.config 下。 */
    @Test
    @SuppressWarnings("unchecked")
    void follow_redirects_is_configured_in_openfeign_binding_namespace() throws IOException {
        Yaml yaml = new Yaml();
        Map<String, Object> doc = yaml.load(
            Files.readString(Paths.get("src/main/resources/application-manager.yml"), StandardCharsets.UTF_8));

        Map<String, Object> spring = (Map<String, Object>) doc.get("spring");
        assertThat(spring).as("yml 缺 spring 树").isNotNull();
        Map<String, Object> cloud = (Map<String, Object>) spring.get("cloud");
        assertThat(cloud).as("yml 缺 spring.cloud 树").isNotNull();
        Map<String, Object> openfeign = (Map<String, Object>) cloud.get("openfeign");
        assertThat(openfeign).as("yml 缺 spring.cloud.openfeign 树").isNotNull();
        Map<String, Object> client = (Map<String, Object>) openfeign.get("client");
        Map<String, Object> config = client == null ? null : (Map<String, Object>) client.get("config");
        assertThat(config).as("yml 缺 spring.cloud.openfeign.client.config 树").isNotNull();

        for (String allowed : FeignClientRegistry.allowedClients()) {
            Map<String, Object> cfg = (Map<String, Object>) config.get(allowed);
            assertThat(cfg)
                .as("允许注入关联 Header 的客户端 %s 缺 spring.cloud.openfeign.client.config.%s 配置块", allowed, allowed)
                .isNotNull();
            assertThat(cfg.get("followRedirects"))
                .as("客户端 %s 的 followRedirects 必须在 spring.cloud.openfeign 绑定命名空间显式为 false（防跨源 3xx 携带关联 Header）", allowed)
                .isEqualTo(false);
        }

        // 死命名空间守卫：顶层 feign.client.config.* 下的 followRedirects 不被 openfeign 4.x 读取，不得残留
        Map<String, Object> feign = (Map<String, Object>) doc.get("feign");
        if (feign != null) {
            Map<String, Object> fc = (Map<String, Object>) feign.get("client");
            Map<String, Object> fcfg = fc == null ? null : (Map<String, Object>) fc.get("config");
            if (fcfg != null) {
                for (Object c : fcfg.values()) {
                    if (c instanceof Map) {
                        assertThat(((Map<String, Object>) c).containsKey("followRedirects"))
                            .as("顶层 feign.client.config.* 是 openfeign 4.x 死命名空间，followRedirects 落此树不生效（须迁 spring.cloud.openfeign.client.config）")
                            .isFalse();
                    }
                }
            }
        }
    }
}

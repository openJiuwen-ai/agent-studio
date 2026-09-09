/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.http.converter.StringHttpMessageConverter;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * OpenAPI 文档归档器 — 服务启动后自动将 springdoc 生成的 OpenAPI 文档转储到本地目录。
 *
 * <p>触发条件：
 * <ol>
 *   <li>{@code springdoc.api-docs.enabled=true}（即 {@code API_DOCS_ENABLED=true}）— 文档端点已开启</li>
 *   <li>从 CWD 向上查找 {@code docs/} 目录（最多 5 级），找到则归档，否则视为 Docker 环境跳过</li>
 * </ol>
 *
 * <p>归档路径可通过 {@code studio.docs.archive-dir} 属性配置，默认 {@code docs/api}。</p>
 *
 * <p>用法：本地开发设 {@code API_DOCS_ENABLED=true} 重启服务，文档自动更新到 {@code docs/api/}，
 * 通过 {@code git diff} 检查变更后提交。生产环境 Docker 镜像无 {@code docs/} 目录，自动跳过。</p>
 */
@Component
@ConditionalOnProperty(name = "springdoc.api-docs.enabled", havingValue = "true")
public class OpenApiDocArchiver {

    private static final Logger logger = LoggerFactory.getLogger(OpenApiDocArchiver.class);

    @Value("${server.port:8080}")
    private int serverPort;

    @Value("${studio.docs.archive-dir:docs/api/studio-manager}")
    private String archiveDir;

    @EventListener(ApplicationReadyEvent.class)
    public void archive() {
        Path projectRoot = findProjectRoot();
        if (projectRoot == null) {
            logger.info("[OpenAPI] docs/ not found, skipping archiving (likely Docker environment)");
            return;
        }

        Path archivePath = projectRoot.resolve(archiveDir);
        try {
            Files.createDirectories(archivePath);
        } catch (Exception e) {
            logger.warn("[OpenAPI] Failed to create archive directory {}: {}", archivePath, e.getMessage());
            return;
        }

        String baseUrl = "http://localhost:" + serverPort;
        RestTemplate restTemplate = new RestTemplate();
        restTemplate.getMessageConverters().forEach(c -> {
            if (c instanceof StringHttpMessageConverter sc) {
                sc.setDefaultCharset(StandardCharsets.UTF_8);
            }
        });

        fetchAndSave(restTemplate, baseUrl + "/v3/api-docs.yaml", archivePath.resolve("openapi.yaml"));

        logger.info("[OpenAPI] Archive complete. Check git diff for changes: git diff --stat {}", archivePath);
    }

    private Path findProjectRoot() {
        Path p = Paths.get("").toAbsolutePath();
        for (int i = 0; i < 5; i++) {
            if (Files.exists(p.resolve("docs"))) {
                return p;
            }
            if (p.getParent() == null || p.getParent().equals(p)) {
                break;
            }
            p = p.getParent();
        }
        return null;
    }

    private void fetchAndSave(RestTemplate restTemplate, String url, Path outputFile) {
        try {
            String content = restTemplate.getForObject(url, String.class);
            if (content == null || content.isBlank()) {
                logger.warn("[OpenAPI] Empty response from {}", url);
                return;
            }
            Files.writeString(outputFile, content, StandardCharsets.UTF_8);
            logger.info("[OpenAPI] Archived: {} ({} chars)", outputFile.getFileName(), content.length());
        } catch (Exception e) {
            logger.warn("[OpenAPI] Failed to fetch from {}: {}", url, e.getMessage());
        }
    }
}

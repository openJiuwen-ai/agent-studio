/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import lombok.extern.slf4j.Slf4j;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipFile;

/**
 * ZIP包校验工具类
 * 用于严格校验skill-creator.zip文件的格式、大小、安全性以及SKILL.md文件的内容
 *
 */
@Slf4j
public class ZipValidationUtils {

    private static ZipFile openZipFile(File zipFile) throws IOException {
        try {
            return new ZipFile(zipFile);
        } catch (ZipException e) {
            return new ZipFile(zipFile, Charset.forName("GBK"));
        }
    }

    private static final long MAX_ZIP_SIZE = 10L * 1024 * 1024; // 10MB

    private static final long MAX_EXTRACTED_SIZE = 100L * 1024 * 1024; // 100MB

    private static final int MAX_ENTRY_COUNT = 500;

    private static final int MAX_DEPTH = 10;

    private static final Set<String> ALLOWED_FRONTMATTER_FIELDS = Set.of(
            "name", "description", "license", "allowed-tools", "metadata", "compatibility"
            , "version", "category", "sources", "- https"
    );

    private static final Pattern NAME_PATTERN = Pattern.compile("^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$");

    private static final Pattern DESCRIPTION_PATTERN = Pattern.compile("^[^<]+$");


    /**
     * 存储解析后的SKILL.md文件frontmatter
     */
    private static Map<String, Object> frontmatter = new LinkedHashMap<>();


    /**
     * 获取解析后的frontmatter
     *
     * @return frontmatter数据
     */
    public static Map<String, Object> getFrontmatter() {
        return new LinkedHashMap<>(frontmatter);
    }


    /**
     * 校验ZIP包
     *
     * @param zipFile ZIP文件
     * @throws AgentStudioException 校验失败时抛出异常
     */
    public static void validateZipFile(File zipFile) {
        // 1. 文件格式检查
        validateFileFormat(zipFile);

        // 2. 文件大小检查
        validateFileSize(zipFile);

        // 3. ZIP安全检查
        validateZipSecurity(zipFile);

        // 4. 解压后内容检查
        validateExtractedContent(zipFile);
    }

    /**
     * 验证文件格式
     */
    private static void validateFileFormat(File zipFile) {
        if (!zipFile.exists() || !zipFile.isFile()) {
            log.error("The file does not exist or is not a file: {}", zipFile.getAbsolutePath());
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        // Magic Number检查 (ZIP文件头特征)
        if (!isZipFile(zipFile)) {
            log.error("Invalid file type.");
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_TYPE);
        }
    }

    /**
     * 验证ZIP文件的Magic Number
     */
    public static boolean isZipFile(File zipFile) {
        try (FileInputStream fis = new FileInputStream(zipFile);
             BufferedInputStream bis = new BufferedInputStream(fis)) {

            byte[] header = new byte[4];
            int bytesRead = bis.read(header);

            // ZIP文件头签名: 0x50 0x4B 0x03 0x04
            return isValidZipHeader(header, bytesRead);
        } catch (IOException e) {
            log.error("Failed to check the magic number of the ZIP file: {}", e.getMessage(), e);
            return false;
        }
    }

    /**
     * 验证 SKILL 解压前文件大小
     */
    private static void validateFileSize(File zipFile) {
        long fileSize = zipFile.length();
        if (fileSize > MAX_ZIP_SIZE) {
            log.error("The file size exceeds the limit: {}", fileSize);
            throw new AgentStudioException(StudioError.SKILL_SIZE_EXCEED_LIMIT);
        }
    }

    /**
     * 验证ZIP安全性
     */
    private static void validateZipSecurity(File zipFile) {
        try (ZipFile zip = openZipFile(zipFile)) {
            Enumeration<? extends ZipEntry> entries = zip.entries();

            int entryCount = 0;
            long totalSize = 0L;
            Map<String, Integer> pathDepthMap = new HashMap<>();

            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                entryCount++;

                // 条目数检查
                if (entryCount > MAX_ENTRY_COUNT) {
                    log.error("The number of ZIP entries exceeds the limit. A maximum of {} entries are allowed.",
                            MAX_ENTRY_COUNT);
                    throw new AgentStudioException(StudioError.ZIP_FILE_COUNT_EXCEED_LIMIT);
                }

                // 嵌套ZIP检查
                if (entry.getName().toLowerCase(Locale.ROOT).endsWith(".zip")) {
                    log.error("ZIP files cannot be nested in other ZIP files: {}", entry.getName());
                    throw new AgentStudioException(StudioError.FILE_NESTED_ZIP);
                }

                // 路径深度检查
                int depth = calculatePathDepth(entry.getName());
                if (depth > MAX_DEPTH) {
                    log.error("The depth of the ZIP file path is too deep. The maximum number of allowed levels is {}." +
                            " Current path: {}", MAX_DEPTH, entry.getName());
                    throw new AgentStudioException(StudioError.ZIP_PATH_TOO_DEEP);
                }

                // 路径穿越检查
                if (containsPathTraversal(entry.getName())) {
                    log.error("The ZIP file contains a path traversal vulnerability, an insecure path: {}", entry.getName());
                    throw new AgentStudioException(StudioError.INSECURE_PATH);
                }

                // 符号链接检查
                if (isSymbolicLink(entry)) {
                    log.error("The ZIP file contains symbolic links, unsafe paths: {}", entry.getName());
                    throw new AgentStudioException(StudioError.UNSAFE_PATH);
                }

                totalSize += entry.getSize();
                pathDepthMap.put(entry.getName(), depth);

            }

            // 解压后总大小检查
            if (totalSize > MAX_EXTRACTED_SIZE) {
                log.error("The extracted size exceeds the limit, the maximum size is 100 MB: {}", formatFileSize(totalSize));
                throw new AgentStudioException(StudioError.SKILL_SIZE_EXCEED_LIMIT);
            }

        } catch (IOException e) {
            log.error("ZIP verification failed: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }
    }

    /**
     * 计算路径深度
     */
    private static int calculatePathDepth(String path) {
        if (path == null || path.isEmpty()) {
            return 0;
        }

        String normalizedPath = path.replace('\\', '/');
        String[] parts = normalizedPath.split("/");

        // 移除空字符串（连续分隔符或路径末尾的分隔符）
        int nonEmptyParts = 0;
        for (String part : parts) {
            if (!part.isEmpty()) {
                nonEmptyParts++;
            }
        }

        return nonEmptyParts;
    }

    /**
     * 检查路径穿越
     */
    private static boolean containsPathTraversal(String path) {
        return path.contains("../") || path.contains("..\\") || path.startsWith("..");
    }

    /**
     * 检查是否为符号链接
     */
    private static boolean isSymbolicLink(ZipEntry entry) {
        return isWindowsSymlink(entry) || isUnixSymlink(entry);
    }

    /**
     * 检查Windows符号链接特征
     */
    private static boolean isWindowsSymlink(ZipEntry entry) {
        String name = entry.getName().toLowerCase(Locale.ROOT);
        String fileName = name.substring(name.lastIndexOf('/') + 1);
        return fileName.endsWith(".lnk") || fileName.endsWith(".url") ||
                fileName.equals("desktop.ini");
    }

    /**
     * 检查Unix符号链接特征
     */
    private static boolean isUnixSymlink(ZipEntry entry) {
        String name = entry.getName();
        String fileName = name.substring(name.lastIndexOf('/') + 1);
        return fileName.startsWith("._") || fileName.endsWith(".symlink") ||
                fileName.endsWith(".link");
    }

    /**
     * 验证解压后的内容
     */
    private static void validateExtractedContent(File zipFile) {
        Path tempDir = null;
        String zipFileName;
        try {
            zipFileName = zipFile.getName().substring(0, zipFile.getName().lastIndexOf('.'));

            // 创建临时目录
            tempDir = Files.createTempDirectory(zipFileName);

            Path tempDirForValidation = tempDir.resolveSibling(zipFileName);

            // 解压ZIP文件
            unzip(zipFile, tempDirForValidation);

            // 验证目录结构
            validateDirectoryStructure(tempDirForValidation);

            // 验证SKILL.md文件
            validateSkillMdFile(tempDirForValidation);

        } catch (IOException e) {
            log.error("Failed to verify the decompressed content: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.RESOURCE_READER_ERROR);
        } finally {
            // 清理临时文件
            if (tempDir != null) {
                deleteDirectoryQuietly(tempDir);
            }
        }
    }

    /**
     * 解压ZIP文件
     */
    private static void unzip(File zipFile, Path destDir) throws IOException {
        try (ZipFile zip = openZipFile(zipFile)) {
            Enumeration<? extends ZipEntry> entries = zip.entries();

            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();

                if (entry.isDirectory()) {
                    continue;
                }

                Path destPath = destDir.resolve(entry.getName());

                // 确保父目录存在
                Files.createDirectories(destPath.getParent());

                // 解压文件
                try (InputStream is = zip.getInputStream(entry);
                     OutputStream os = Files.newOutputStream(destPath)) {
                    byte[] buffer = new byte[1024];
                    int len;
                    while ((len = is.read(buffer)) > 0) {
                        os.write(buffer, 0, len);
                    }
                }
            }
        }
    }

    /**
     * 验证目录结构
     */
    private static void validateDirectoryStructure(Path baseDir) throws IOException {
        try (Stream<Path> paths = Files.walk(baseDir)) {
            List<Path> allDirs = paths.filter(Files::isDirectory).filter(p -> !p.equals(baseDir)).toList();

            // 过滤掉空目录
            List<Path> nonEmptyDirs = new ArrayList<>();
            for (Path dir : allDirs) {
                try (Stream<Path> dirContents = Files.list(dir)) {
                    if (dirContents.findAny().isPresent()) {
                        nonEmptyDirs.add(dir);
                    }
                }
            }

            // 如果有多个非空目录，则检查是否都是有效的工作目录（包含SKILL.md）
            List<Path> skillDirs = new ArrayList<>();
            for (Path dir : nonEmptyDirs) {
                Path skillMdFile = dir.resolve("SKILL.md");
                if (Files.exists(skillMdFile)) {
                    skillDirs.add(dir);
                }
            }

            // 情况1：只有一个包含SKILL.md的目录
            if (skillDirs.size() == 1) {
                return; // 有效结构
            }

            // 情况2：SKILL.md直接在根目录下
            Path rootSkillMd = baseDir.resolve("SKILL.md");
            if (Files.exists(rootSkillMd) && nonEmptyDirs.size() <= 1) {
                return; // 有效结构
            }

            // 其他情况都是无效的
            log.error("Directory check failed - Directories: {}, Non-empty: {}, Has SKILL.md: {}",
                    skillDirs.size(), nonEmptyDirs.size(), Files.exists(rootSkillMd));
            throw new AgentStudioException(StudioError.FILES_NUMBER_DOES_NOT_MATCH);
        }
    }

    /**
     * 验证SKILL.md文件
     */
    private static void validateSkillMdFile(Path baseDir) throws IOException {
        try (Stream<Path> paths = Files.walk(baseDir)) {
            Path skillMdFile = paths.filter(p ->
                    p.getFileName() != null &&
                            "SKILL.md".equalsIgnoreCase(p.getFileName().toString())
            ).findFirst().orElse(null);

            if (skillMdFile == null) {
                log.error("The ZIP file does not contain a SKILL.md file.");
                throw new AgentStudioException(StudioError.SKILL_MD_IS_MISSING);
            }

            // 读取文件内容
            String content = Files.readString(skillMdFile);

            // 解析YAML
            Map<String, Object> frontmatterYaml = parseYamlFrontmatter(content);

            // 验证frontmatterYaml字段
            validateFrontmatter(frontmatterYaml, skillMdFile);
        }
    }

    /**
     * 解析YAML frontmatter
     */
    private static Map<String, Object> parseYamlFrontmatter(String content) {
        Map<String, Object> result = new LinkedHashMap<>();

        // 重置frontmatter，避免多次调用时的数据残留
        ZipValidationUtils.frontmatter = new LinkedHashMap<>();

        // YAML frontmatter解析
        if (content.startsWith("---")) {
            int endFront = content.indexOf("---", 3);
            if (endFront != -1) {
                String frontmatterText = content.substring(3, endFront).trim();

                // 解析key: value格式
                String[] lines = frontmatterText.split("\n");
                for (String rawLine : lines) {
                    if (!rawLine.isEmpty() && (rawLine.charAt(0) == ' ' || rawLine.charAt(0) == '\t')) {
                        continue;
                    }

                    String line = rawLine.trim();
                    if (line.isEmpty() || line.startsWith("#")) {
                        continue;
                    }

                    int colonIndex = line.indexOf(':');
                    if (colonIndex > 0) {
                        String key = line.substring(0, colonIndex).trim();
                        String value = line.substring(colonIndex + 1).trim();

                        // 处理布尔值
                        if ("true".equalsIgnoreCase(value)) {
                            value = "true";
                        } else if ("false".equalsIgnoreCase(value)) {
                            value = "false";
                        }

                        result.put(key, value);
                        // 同时保存到静态变量中
                        ZipValidationUtils.frontmatter.put(key, value);
                    }
                }
            }
        }

        return result;
    }

    /**
     * 验证frontmatter字段
     */
    private static void validateFrontmatter(Map<String, Object> frontmatter, Path skillMdFile) {

        // 检查白名单字段
        for (String field : frontmatter.keySet()) {
            if (!ALLOWED_FRONTMATTER_FIELDS.contains(field)) {
                log.error("Invalid frontmatter field: {}", field);
                throw new AgentStudioException(StudioError.SKILL_MD_INVALID_FIELD);
            }
        }

        // 检查必填字段
        Object name = frontmatter.get("name");
        if (name == null || name.toString().trim().isEmpty()) {
            log.error("The name cannot be empty.");
            throw new AgentStudioException(StudioError.NAME_FIELD_MISSING);
        } else {
            validateName(name.toString());
        }

        Object description = frontmatter.get("description");
        if (description == null || description.toString().trim().isEmpty()) {
            log.error("The description cannot be empty.");
            throw new AgentStudioException(StudioError.DESCRIPTION_FIELD_MISSING);
        } else {
            validateDescription(description.toString());
        }

        // 检查compatibility字段
        Object compatibility = frontmatter.get("compatibility");
        if (compatibility != null) {
            validateCompatibility(compatibility.toString());
        }

        // 验证目录名与name字段一致
        if (!isValidDirectoryName(skillMdFile, name.toString())) {
            log.error("The directory name and the name field in the SKILL.md file do not match.");
            throw new AgentStudioException(StudioError.NAME_FORMAT_MISMATCH);
        }
    }

    /**
     * 验证name字段
     */
    private static void validateName(String name) {
        if (name.isEmpty() || name.length() > 64) {
            log.error("The length must be between 1 and 64 characters.");
            throw new AgentStudioException(StudioError.NAME_FORMAT_MISMATCH);
        }

        if (!NAME_PATTERN.matcher(name).matches()) {
            log.error("The name field does not meet the specifications.");
            throw new AgentStudioException(StudioError.NAME_FORMAT_MISMATCH);
        }
    }

    /**
     * 验证description字段
     */
    private static void validateDescription(String description) {
        if (description.isEmpty() || description.length() > 1024) {
            log.error("The length must be between 1 and 1024 characters.");
            throw new AgentStudioException(StudioError.DESCRIPTION_LENGTH_EXCEED);
        }

        if (!DESCRIPTION_PATTERN.matcher(description).matches()) {
            log.error("Cannot contain XML tags");
            throw new AgentStudioException(StudioError.INVALID_CHARACTER);
        }
    }

    /**
     * 验证compatibility字段
     */
    private static void validateCompatibility(String compatibility) {
        if (compatibility.length() > 500) {
            log.error("The length must be between 1 and 500 characters.");
            throw new AgentStudioException(StudioError.COMPATIBILITY_LENGTH_EXCEED);
        }
    }

    /**
     * 验证目录名
     */
    private static boolean isValidDirectoryName(Path skillMdFile, String nameField) {
        Path parentDir = skillMdFile.getParent();

        // 如果SKILL.md在根目录下，跳过目录名验证
        if (parentDir == null || !parentDir.isAbsolute()) {
            return true;
        }

        // 获取SKILL.md所在目录的名称
        try {
            Path limitedParent = parentDir.getFileName();
            if (limitedParent != null && limitedParent.getFileName() != null) {
                String dirName = limitedParent.getFileName().toString();
                return dirName.equalsIgnoreCase(nameField);
            }
        } catch (Exception e) {
            log.error("Unexpected error while validating directory name: {}", e.getMessage());
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        return true;
    }

    /**
     * 删除目录
     */
    private static void deleteDirectoryQuietly(Path path) {
        try {
            try (Stream<Path> paths = Files.walk(path)) {
                paths.sorted(Comparator.reverseOrder())
                        .forEach(p -> {
                            try {
                                Files.deleteIfExists(p);
                            } catch (IOException e) {
                                log.warn("The file cannot be deleted: {}", p, e);
                            }
                        });
            }
        } catch (IOException e) {
            log.warn("The directory cannot be deleted: {}", path, e);
        }
    }

    /**
     * 格式化文件大小
     */
    private static String formatFileSize(long size) {
        if (size < 1024) {
            return size + " B";
        } else if (size < 1024 * 1024) {
            return String.format("%.1f KB", size / 1024.0);
        } else {
            return String.format("%.1f MB", size / (1024.0 * 1024.0));
        }
    }

    private static boolean isValidZipHeader(byte[] header, int bytesRead) {
        if (bytesRead != 4) {
            return false;
        }
        return header[0] == 0x50 && header[1] == 0x4B && header[2] == 0x03 && header[3] == 0x04;
    }

}

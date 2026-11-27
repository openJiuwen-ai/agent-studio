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
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
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
import java.util.zip.ZipOutputStream;

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

    private static final Pattern NAME_PATTERN = Pattern.compile("^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$");

    private static final Pattern DESCRIPTION_PATTERN = Pattern.compile("^[^<]+$");


    /**
     * 校验ZIP包并返回解析后的 frontmatter。
     *
     * <p>本方法不再依赖静态变量传递 frontmatter，避免并发导入时被其他线程覆盖。
     * 调用方可直接通过返回值获取 SKILL.md 中的 name/description 等字段。</p>
     *
     * @param zipFile ZIP文件
     * @return 解析后的 frontmatter
     * @throws AgentStudioException 校验失败时抛出异常
     */
    public static Map<String, Object> validateZipFile(File zipFile) {
        // 1. 文件格式检查
        validateFileFormat(zipFile);

        // 2. 文件大小检查
        validateFileSize(zipFile);

        // 3. ZIP安全检查
        validateZipSecurity(zipFile);

        // 4. 解压后内容检查（内部解析 frontmatter 并返回）
        return validateExtractedContent(zipFile);
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
     * 检查路径穿越。
     *
     * <p>拦截以下三类恶意条目名：</p>
     * <ol>
     *   <li>相对路径穿越：包含 {@code ../} 或 {@code ..\}，或以 {@code ..} 开头；</li>
     *   <li>绝对路径条目：以 {@code /} 或 {@code \} 开头，或以 Windows 盘符（如 {@code C:}）开头，
     *       避免 {@code destDir.resolve(entry.getName())} 写出到临时目录之外；</li>
     *   <li>盘符分隔：包含 {@code :} 作为路径段（Windows 盘符）。</li>
     * </ol>
     */
    private static boolean containsPathTraversal(String path) {
        if (path == null || path.isEmpty()) {
            return false;
        }
        if (path.contains("../") || path.contains("..\\") || path.startsWith("..")) {
            return true;
        }
        // 绝对路径条目（Unix 或 Windows）
        if (path.charAt(0) == '/' || path.charAt(0) == '\\') {
            return true;
        }
        // Windows 盘符绝对路径，如 C:\ 或 C:/（长度 >= 2 且第 2 个字符为 ':'）
        if (path.length() >= 2 && path.charAt(1) == ':') {
            return true;
        }
        return false;
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
     * 验证解压后的内容。
     *
     * <p>解压到临时目录的根级（不再拼接 zipFileName 子层），使平铺包的 SKILL.md 真正位于根级，
     * 单文件夹包的 {name}/SKILL.md 也位于根级下。tempDir 即为 extractionRoot，向下游透传，
     * 供 isValidDirectoryName() 判断平铺结构使用。</p>
     *
     * @return 从 SKILL.md 解析得到的 frontmatter
     */
    private static Map<String, Object> validateExtractedContent(File zipFile) {
        Path tempDir = null;
        try {
            // 直接在 tempDir 根解压，不再创建 zipFileName 子目录
            tempDir = Files.createTempDirectory("skill-validate");
            unzip(zipFile, tempDir);

            // 验证目录结构
            validateDirectoryStructure(tempDir);

            // 验证SKILL.md文件并返回 frontmatter
            return validateSkillMdFile(tempDir);

        } catch (IOException e) {
            log.error("Failed to verify the decompressed content: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.RESOURCE_READER_ERROR);
        } finally {
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
     * 验证目录结构。
     *
     * <p>平铺结构优先判定：根级有 SKILL.md 即视为平铺包（即使不带 frontmatter，
     * 交给 validateFrontmatter 报正确错误码）。但如果根级 SKILL.md 不带 frontmatter
     * 而子目录有带 frontmatter 的 SKILL.md，则回落到情况2（根级是普通文档、真正 skill 在子目录）。
     * 根级带 frontmatter 时，显式禁止子目录再出现带 frontmatter 的 SKILL.md，避免查找歧义。
     * 子目录中不带 frontmatter 的同名普通文档不影响判定。</p>
     *
     * <p><b>单文件夹结构的根级约束</b>：仅认可直接位于子目录根级的带 frontmatter 的 SKILL.md
     * （即 {@code baseDir/<name>/SKILL.md}）。</p>
     * <ul>
     *   <li>禁止 {@code a/b/SKILL.md}：即带 frontmatter 的 SKILL.md 嵌套在二级及更深子目录，
     *       即使 name=b 也无法通过——否则会以原始结构上传，生成不符合
     *       {@code {name}/SKILL.md} 规范的制品，下游消费方可能解析失败；
     *       不带 frontmatter 的同名普通文档不受此约束；</li>
     *   <li>skillDirs.size() != 1 拒绝：含带 frontmatter 的 SKILL.md 的直接子目录数量必须恰为 1；</li>
     *   <li><b>根级非空目录唯一性</b>：根级非空目录总数也必须恰为 1（即 skillDirs 那个）。
     *       否则如 {@code assets/ + my-skill/SKILL.md} 会通过校验并按原结构上传，
     *       详情页解压后 innerData[0] 按 sortTree 字母序取到 assets/ 而非 my-skill/，
     *       导致 openSkillMd 在 assets/SKILL.md 找不到文件、无法自动打开 SKILL.md
     *       （详见检视意见 Medium Priority #415）。</li>
     * </ul>
     */
    private static void validateDirectoryStructure(Path baseDir) throws IOException {
        // 情况1：根目录有 SKILL.md（平铺结构），允许任意数量的附属文件夹/文件
        // 根级 SKILL.md 存在即进入平铺分支（即使不带 frontmatter，交给 validateFrontmatter 报正确错误码）
        // 但如果子目录有带 frontmatter 的 SKILL.md 而根级的不带，说明根级是普通文档、真正 skill 在子目录 → 回落到情况2
        Path rootSkillMd = baseDir.resolve("SKILL.md");
        if (Files.exists(rootSkillMd)) {
            boolean rootHasFrontmatter = isSkillMdWithFrontmatter(rootSkillMd);
            // 检查子目录是否有带 frontmatter 的 SKILL.md
            long childSkillMdWithFrontmatter = 0;
            try (Stream<Path> paths = Files.walk(baseDir)) {
                childSkillMdWithFrontmatter = paths
                        .filter(p -> !p.equals(rootSkillMd))
                        .filter(p -> p.getFileName() != null
                                && "SKILL.md".equalsIgnoreCase(p.getFileName().toString()))
                        .filter(ZipValidationUtils::isSkillMdWithFrontmatter)
                        .count();
            }
            if (rootHasFrontmatter) {
                // 根级带 frontmatter：不允许子目录再出现带 frontmatter 的 SKILL.md
                if (childSkillMdWithFrontmatter > 0) {
                    log.error("Multiple SKILL.md with frontmatter detected: root + {} child", childSkillMdWithFrontmatter);
                    throw new AgentStudioException(StudioError.FILES_NUMBER_DOES_NOT_MATCH);
                }
                return; // 有效结构（平铺）
            } else if (childSkillMdWithFrontmatter == 0) {
                // 根级不带 frontmatter，子目录也没有带 frontmatter 的 SKILL.md
                // 仍按平铺处理，交给 validateFrontmatter 报 NAME_FIELD_MISSING 等正确错误码
                return;
            }
            // 根级不带 frontmatter 但子目录有带 frontmatter 的 → 回落到情况2
        }

        // 情况2：根目录无 SKILL.md，需恰有 1 个直接子目录含 SKILL.md（单文件夹结构）
        // 仅认可 baseDir/<name>/SKILL.md，禁止 a/b/SKILL.md 嵌套结构。
        List<Path> skillDirs = new ArrayList<>();
        try (Stream<Path> allPaths = Files.walk(baseDir)) {
            List<Path> allDirs = allPaths.filter(Files::isDirectory).filter(p -> !p.equals(baseDir)).toList();

            // 过滤掉空目录，仅保留非空目录
            List<Path> nonEmptyDirs = new ArrayList<>();
            for (Path dir : allDirs) {
                try (Stream<Path> dirContents = Files.list(dir)) {
                    if (dirContents.findAny().isPresent()) {
                        nonEmptyDirs.add(dir);
                    }
                }
            }

            // 仅取直接位于 baseDir 下且自身根级含 SKILL.md 的子目录
            // 与前端策略2对齐：优先看带 frontmatter 的候选来消歧
            List<Path> allSkillDirs = new ArrayList<>();
            List<Path> frontmatterSkillDirs = new ArrayList<>();
            for (Path dir : nonEmptyDirs) {
                Path skillMdAtRoot = dir.resolve("SKILL.md");
                if (Files.exists(skillMdAtRoot)) {
                    boolean hasFrontmatter = isSkillMdWithFrontmatter(skillMdAtRoot);
                    // 嵌套检查只对带 frontmatter 的 SKILL.md 生效
                    // 不带 frontmatter 的同名普通文档（如 my-skill/docs/SKILL.md）不参与结构判定
                    if (hasFrontmatter) {
                        Path rel = baseDir.relativize(dir);
                        if (rel.getNameCount() != 1) {
                            log.error("Nested SKILL.md directory must be a direct child of base, got: {}", rel);
                            throw new AgentStudioException(StudioError.FILES_NUMBER_DOES_NOT_MATCH);
                        }
                        frontmatterSkillDirs.add(dir);
                    }
                    allSkillDirs.add(dir);
                }
            }

            // 优先用带 frontmatter 的候选消歧；若全部不带 frontmatter，用全部候选
            // 这样单文件夹结构下 SKILL.md 缺字段时仍能选中并交给 validateFrontmatter 报正确错误码
            skillDirs = frontmatterSkillDirs.size() > 0 ? frontmatterSkillDirs : allSkillDirs;

            if (skillDirs.size() != 1) {
                log.error("Directory check failed - skillDirs: {}, frontmatterDirs: {}, allDirs: {}, nonEmpty: {}",
                        skillDirs.size(), frontmatterSkillDirs.size(), allSkillDirs.size(), nonEmptyDirs.size());
                throw new AgentStudioException(StudioError.FILES_NUMBER_DOES_NOT_MATCH);
            }

            // 根级非空目录唯一性：含 SKILL.md 的目录必须是根级唯一的非空目录。
            // 否则如 assets/ + my-skill/SKILL.md 会通过校验，详情页 sortTree 按字母序
            // 取 innerData[0] = assets/，openSkillMd 在 assets/SKILL.md 找不到文件。
            Path skillDir = skillDirs.get(0);
            for (Path dir : nonEmptyDirs) {
                // 仅看 baseDir 的直接子目录（深度=1），子目录内部的非空目录不算
                Path rel = baseDir.relativize(dir);
                if (rel.getNameCount() == 1 && !dir.equals(skillDir)) {
                    log.error("Root-level has extra non-empty directory besides skill dir: {}", rel);
                    throw new AgentStudioException(StudioError.FILES_NUMBER_DOES_NOT_MATCH);
                }
            }

            return; // 有效结构（单文件夹）
        }
    }

    /**
     * 验证SKILL.md文件，并返回解析得到的 frontmatter。
     *
     * <p>三级查找策略（与 validateDirectoryStructure 对齐）：
     * <ol>
     *   <li>根级带 frontmatter 的 SKILL.md → 直接选用</li>
     *   <li>任意位置带 frontmatter 的 SKILL.md → 用兜底结果（避免选中子目录普通文档）</li>
     *   <li>任意位置 SKILL.md（可能缺字段）→ 选中让 validateFrontmatter 报正确错误码</li>
     * </ol>
     * 同时将 baseDir 作为 extractionRoot 透传给 validateFrontmatter / isValidDirectoryName。</p>
     *
     * @param baseDir 解压根目录（即 tempDir）
     * @return 解析得到的 frontmatter
     */
    private static Map<String, Object> validateSkillMdFile(Path baseDir) throws IOException {
        // 优先取根级带 frontmatter 的 SKILL.md（与 validateDirectoryStructure 情况1 对齐）
        // 根级 SKILL.md 不带 frontmatter 时，回落到兜底查找子目录中带 frontmatter 的 SKILL.md
        Path skillMdFile = baseDir.resolve("SKILL.md");
        if (!Files.exists(skillMdFile) || !isSkillMdWithFrontmatter(skillMdFile)) {
            // 兜底：查找第一个带 frontmatter 的 SKILL.md（单文件夹结构下命中 {name}/SKILL.md）
            // 不带 frontmatter 的同名文件（如子目录普通文档）不会被选中
            Path found = null;
            try (Stream<Path> paths = Files.walk(baseDir)) {
                found = paths
                        .filter(p -> p.getFileName() != null
                                && "SKILL.md".equalsIgnoreCase(p.getFileName().toString()))
                        .filter(ZipValidationUtils::isSkillMdWithFrontmatter)
                        .findFirst().orElse(null);
            }
            // 如果兜底找到了带 frontmatter 的，用兜底结果；
            // 如果兜底没找到但根级 SKILL.md 存在（缺 frontmatter），仍选根级文件让 validateFrontmatter 报正确错误码
            if (found != null) {
                skillMdFile = found;
            } else if (!Files.exists(skillMdFile)) {
                // 既没有根级 SKILL.md，也没找到带 frontmatter 的 SKILL.md
                // 尝试找任意 SKILL.md（可能缺字段，交给 validateFrontmatter 报正确错误码）
                try (Stream<Path> paths = Files.walk(baseDir)) {
                    skillMdFile = paths.filter(p ->
                            p.getFileName() != null &&
                                    "SKILL.md".equalsIgnoreCase(p.getFileName().toString())
                    ).findFirst().orElse(null);
                }
            }
        }

        if (skillMdFile == null) {
            log.error("The ZIP file does not contain a SKILL.md file.");
            throw new AgentStudioException(StudioError.SKILL_MD_IS_MISSING);
        }

        // 读取文件内容
        String content = Files.readString(skillMdFile);

        // 解析YAML
        Map<String, Object> frontmatterYaml = parseYamlFrontmatter(content);

        // 验证frontmatterYaml字段，并将 baseDir 作为 extractionRoot 透传
        validateFrontmatter(frontmatterYaml, skillMdFile, baseDir);

        return frontmatterYaml;
    }

    /**
     * 判断文件是否为带 YAML frontmatter（含 name 和 description 字段）的有效 SKILL.md。
     *
     * <p>用于区分真正的 skill 定义文件与碰巧命名为 SKILL.md 的普通文档。
     * 多模块聚合包（如 ima-skills）的子目录中可能存在同名的普通 md 文档，
     * 它们没有 frontmatter，不应被当作 skill 入口参与结构校验。
     * 与前端 parseSkillMd 判据对齐：同时检查 name 和 description 非空。</p>
     */
    private static boolean isSkillMdWithFrontmatter(Path skillMdPath) {
        try {
            String content = Files.readString(skillMdPath);
            Map<String, Object> fm = parseYamlFrontmatter(content);
            Object name = fm.get("name");
            Object description = fm.get("description");
            return name != null && !name.toString().trim().isEmpty()
                    && description != null && !description.toString().trim().isEmpty();
        } catch (IOException e) {
            log.warn("Failed to read SKILL.md for frontmatter check: {}", skillMdPath);
            return false;
        }
    }

    /**
     * 解析YAML frontmatter。
     *
     * <p>本方法仅返回解析结果，不再写入静态变量，避免并发导入时的线程安全问题。
     * 历史问题：原实现同时写入 ZipValidationUtils.frontmatter 静态变量，
     * 在多线程并发导入时会互相覆盖，导致 frontmatter 数据不一致。</p>
     */
    private static Map<String, Object> parseYamlFrontmatter(String content) {
        Map<String, Object> result = new LinkedHashMap<>();

        // YAML frontmatter解析
        if (content.startsWith("---")) {
            // 查找 frontmatter 结束标记 ---（必须是行首，前面是换行符，避免匹配 block scalar 内容中的缩进 ---）
            int endFront = -1;
            int searchFrom = 3;
            while (true) {
                int pos = content.indexOf("---", searchFrom);
                if (pos == -1) {
                    break;
                }
                // 必须在行首：pos==0（不可能，前面有起始---）或前一个字符是换行
                if (pos > 0 && content.charAt(pos - 1) == '\n') {
                    endFront = pos;
                    break;
                }
                searchFrom = pos + 3;
            }
            if (endFront != -1) {
                String frontmatterText = content.substring(3, endFront).trim();

                // 解析key: value格式
                String[] lines = frontmatterText.split("\n");
                int idx = 0;
                while (idx < lines.length) {
                    String rawLine = lines[idx];
                    if (!rawLine.isEmpty() && (rawLine.charAt(0) == ' ' || rawLine.charAt(0) == '\t')) {
                        idx++;
                        continue;
                    }

                    String line = rawLine.trim();
                    if (line.isEmpty() || line.startsWith("#")) {
                        idx++;
                        continue;
                    }

                    int colonIndex = line.indexOf(':');
                    if (colonIndex > 0) {
                        String key = line.substring(0, colonIndex).trim();
                        String value = line.substring(colonIndex + 1).trim();

                        // YAML block scalar: | (literal) 或 > (folded)，支持 chomping indicator (- +)
                        // 如 |- (strip)、|+ (keep)、>- (strip)、>+ (keep)
                        boolean isBlockScalar = value.equals("|") || value.equals(">")
                                || value.equals("|-") || value.equals("|+")
                                || value.equals(">-") || value.equals(">+");
                        if (isBlockScalar) {
                            boolean isFolded = value.startsWith(">");
                            // chomping indicator (- +) 对 description 用途无实质影响（末尾 trim）
                            StringBuilder blockValue = new StringBuilder();
                            idx++;
                            boolean firstLine = true;
                            boolean lastWasBlankLine = false;
                            while (idx < lines.length) {
                                String bl = lines[idx];
                                // 去除行尾 \r 以兼容 Windows CRLF 换行
                                String blTrimmed = bl.replace("\r", "");
                                // 空行属于 block 内容（段落分隔）
                                if (blTrimmed.isEmpty()) {
                                    idx++;
                                    if (blockValue.length() > 0) {
                                        blockValue.append("\n");
                                    }
                                    lastWasBlankLine = true;
                                    continue;
                                }
                                // 缩进行属于 block scalar
                                if (bl.charAt(0) == ' ' || bl.charAt(0) == '\t') {
                                    if (!firstLine && !lastWasBlankLine) {
                                        // folded 模式换行合并为空格，但空行后不再追加空格（YAML folded 语义）
                                        blockValue.append(isFolded ? " " : "\n");
                                    }
                                    blockValue.append(bl.trim());
                                    firstLine = false;
                                    lastWasBlankLine = false;
                                    idx++;
                                } else {
                                    // 非缩进行且非空行 → block 结束
                                    break;
                                }
                            }
                            value = blockValue.toString().trim();
                            result.put(key, value);
                            continue;
                        }

                        // 处理布尔值
                        if ("true".equalsIgnoreCase(value)) {
                            value = "true";
                        } else if ("false".equalsIgnoreCase(value)) {
                            value = "false";
                        }

                        result.put(key, value);
                    }
                    idx++;
                }
            }
        }

        return result;
    }

    /**
     * 验证frontmatter字段，并校验 SKILL.md 所在目录名是否与 name 字段一致。
     *
     * @param frontmatterYaml 从 SKILL.md 解析得到的 frontmatter
     * @param skillMdFile SKILL.md 文件路径
     * @param extractionRoot 解压根目录（即 tempDir），用于判断平铺结构
     */
    private static void validateFrontmatter(Map<String, Object> frontmatterYaml,
                                            Path skillMdFile,
                                            Path extractionRoot) {

        // 检查必填字段
        Object name = frontmatterYaml.get("name");
        if (name == null || name.toString().trim().isEmpty()) {
            log.error("The name cannot be empty.");
            throw new AgentStudioException(StudioError.NAME_FIELD_MISSING);
        } else {
            validateName(name.toString());
        }

        Object description = frontmatterYaml.get("description");
        if (description == null || description.toString().trim().isEmpty()) {
            log.error("The description cannot be empty.");
            throw new AgentStudioException(StudioError.DESCRIPTION_FIELD_MISSING);
        } else {
            validateDescription(description.toString());
        }

        // 检查compatibility字段
        Object compatibility = frontmatterYaml.get("compatibility");
        if (compatibility != null) {
            validateCompatibility(compatibility.toString());
        }

        // 验证目录名与name字段一致，透传 extractionRoot 用于平铺结构判定
        if (!isValidDirectoryName(skillMdFile, extractionRoot, name.toString())) {
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
     * 验证目录名是否与 SKILL.md frontmatter 中的 name 字段一致。
     *
     * <p>平铺结构判定：parentDir.equals(extractionRoot) 表示 SKILL.md 位于解压根目录，
     * 此时不比对目录名（因为解压根目录名是系统生成的临时目录名，与 skill name 无关）。
     * 单文件夹结构：取父目录最后一段（如 "my-skill"）与 name 比对。</p>
     *
     * <p>注意：原实现用 !parentDir.isAbsolute() 判断平铺结构是无效的——
     * Files.createTempDirectory() 返回的路径始终是绝对路径，该分支恒为 false，
     * 平铺包实际会走到 equalsIgnoreCase(nameField) 比对并几乎必然失败。</p>
     */
    private static boolean isValidDirectoryName(Path skillMdFile, Path extractionRoot, String nameField) {
        Path parentDir = skillMdFile.getParent();

        // 父目录就是解压根 → SKILL.md 在根级（平铺结构），无需比对目录名
        if (parentDir == null || parentDir.equals(extractionRoot)) {
            return true;
        }

        // 单文件夹结构：取父目录最后一段（如 "my-skill"）与 name 比对
        try {
            Path dirNamePart = parentDir.getFileName();
            if (dirNamePart != null) {
                return dirNamePart.toString().equalsIgnoreCase(nameField);
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

    /**
     * 如果是平铺结构（根级有 SKILL.md），重打包为 {name}/ 结构。
     * 单文件夹结构则原样返回入参 zipFile。
     *
     * <p><b>安全约定</b>：本方法内部调用 {@link #unzip(File, Path)} 解压入参 zip，
     * 不再做路径穿越/符号链接/条目数等安全校验。调用方<b>必须</b>先调用
     * {@link #validateZipFile(File)} 完成安全校验后再调用本方法，
     * 否则可能解压恶意构造的 zip 导致路径穿越风险。</p>
     *
     * <p><b>并发安全</b>：重打包产物使用 {@link Files#createTempFile(String, String, File[])}
     * 生成 UUID 前缀的唯一临时文件（与 {@code convertToZipFile} 命名策略一致），
     * 避免多线程并发导入同名 skill 时写同一路径导致互相覆盖或被 finally 误删。
     * 调用方 finally 仅负责清理本方法返回的 zip 文件（若与入参不同），不会误删他人产物。</p>
     *
     * <p><b>边缘场景</b>：若平铺包根级恰好存在与 skillName 同名的子目录
     * （如 SKILL.md + my-skill/helper.py，其中 name=my-skill），
     * {@code Files.createDirectories} 不会报错（目录已存在），
     * {@code Files.list} 循环对该同名目录的 {@code !entry.equals(targetDir)} 为 false → 跳过移动，
     * 该目录原内容保留在 tempDir/my-skill/ 下；后续 zipDirectory(tempDir/my-skill, ...)
     * 会把原内容一并打包。最终结果正确（my-skill/SKILL.md + my-skill/helper.py）。
     * 但若根级存在与 skillName 同名的<b>文件</b>（非目录），{@code Files.createDirectories}
     * 会抛 {@link java.nio.file.FileAlreadyExistsException} → 被泛化为 RESOURCE_READER_ERROR，
     * 本实现显式捕获并返回更精确的 NAME_FORMAT_MISMATCH。</p>
     *
     * @param zipFile 已通过 {@link #validateZipFile(File)} 校验的 zip 文件
     * @param skillName SKILL.md frontmatter 中的 name 字段值
     * @return 重打包后的 zip（平铺结构）或原入参（单文件夹结构）
     */
    public static File repackIfFlat(File zipFile, String skillName) {
        Path tempDir = null;
        File repackedZip = null;  // 提前声明，便于 catch/finally 引用
        try {
            tempDir = Files.createTempDirectory("skill-repack");
            // 复用现有 private unzip（同类内可直接调用）
            unzip(zipFile, tempDir);

            Path rootSkillMd = tempDir.resolve("SKILL.md");
            if (!Files.exists(rootSkillMd) || !isSkillMdWithFrontmatter(rootSkillMd)) {
                // 单文件夹结构，或根级 SKILL.md 不带 frontmatter（非平铺 skill 入口），无需重打包
                return zipFile;
            }

            // 平铺结构：创建 {skillName}/ 子目录，将根级所有条目移入
            Path targetDir = tempDir.resolve(skillName);
            try {
                Files.createDirectories(targetDir);
            } catch (java.nio.file.FileAlreadyExistsException faee) {
                // 根级已存在与 skillName 同名的文件（非目录），结构非法
                log.error("Root-level entry conflicts with skill name directory: {}", skillName);
                throw new AgentStudioException(StudioError.NAME_FORMAT_MISMATCH);
            }
            try (Stream<Path> entries = Files.list(tempDir)) {
                for (Path entry : entries.toList()) {
                    if (!entry.equals(targetDir)) {
                        Path dest = targetDir.resolve(entry.getFileName());
                        Files.move(entry, dest, StandardCopyOption.REPLACE_EXISTING);
                    }
                }
            }

            // 重新打包为 zip：使用唯一临时文件，避免并发导入同名 skill 时互相覆盖
            // Files.createTempFile 要求 prefix 长度 >= 3，NAME_PATTERN 允许单字符 name（如 "a"），
            // 因此对 prefix 补足到至少 3 字符，避免 IllegalArgumentException 冒泡为未受控 500。
            String tempPrefix = skillName + "-";
            if (tempPrefix.length() < 3) {
                tempPrefix = "skill-" + tempPrefix;
            }
            repackedZip = Files.createTempFile(tempPrefix, ".zip").toFile();
            zipDirectory(targetDir, repackedZip, skillName);
            log.info("Repacked flat skill package to {}/ structure: {}", skillName, repackedZip.getName());
            return repackedZip;
        } catch (IOException e) {
            // 异常路径清理半成品 repackedZip，避免磁盘泄漏
            if (repackedZip != null && repackedZip.exists()) {
                if (!repackedZip.delete()) {
                    repackedZip.deleteOnExit();
                    log.warn("Failed to delete partial repacked zip: {}", repackedZip.getAbsolutePath());
                }
            }
            log.error("Failed to repack flat skill: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.RESOURCE_READER_ERROR);
        } catch (IllegalArgumentException e) {
            // 兜底：即使 prefix 规则变化导致 IllegalArgumentException，也转为受控错误码
            log.error("Invalid temp file prefix for skillName: {}", skillName, e);
            throw new AgentStudioException(StudioError.RESOURCE_READER_ERROR);
        } finally {
            if (tempDir != null) {
                deleteDirectoryQuietly(tempDir);  // 复用现有 private 方法
            }
        }
    }

    /**
     * 将 dir 内所有内容打包为 zip，条目名为相对 dir 的相对路径，根目录名为 rootEntryName。
     *
     * <p>注意：不保留空目录条目（原平铺包中的空 __pycache__/ 等会在重打包后丢失，
     * 对 skill 运行时无影响，因 unzip 解压时根据文件父目录会自动重建非空目录）。</p>
     */
    private static void zipDirectory(Path dir, File outputZip, String rootEntryName) throws IOException {
        try (FileOutputStream fos = new FileOutputStream(outputZip);
             ZipOutputStream zos = new ZipOutputStream(fos, StandardCharsets.UTF_8)) {
            try (Stream<Path> stream = Files.walk(dir)) {
                List<Path> files = stream.filter(Files::isRegularFile).toList();
                for (Path file : files) {
                    String relative = rootEntryName + "/" + dir.relativize(file).toString()
                            .replace('\\', '/');
                    ZipEntry entry = new ZipEntry(relative);
                    zos.putNextEntry(entry);
                    Files.copy(file, zos);
                    zos.closeEntry();
                }
            }
        }
    }

}

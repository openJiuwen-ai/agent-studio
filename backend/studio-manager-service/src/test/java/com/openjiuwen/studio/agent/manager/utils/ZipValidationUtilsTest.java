/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

public class ZipValidationUtilsTest {

    @TempDir
    Path tempDir;

    private File validZipFile;
    private File emptyFile;
    private File nonZipFile;
    private File oversizedFile;
    private File nestedZipFile;
    private File pathTraversalFile;
    private File symlinkFile;
    private File deepPathFile;
    private File unsafeFile;

    @BeforeEach
    public void setUp() throws IOException {
        // 创建有效的ZIP文件
        validZipFile = createValidZipFile();

        // 创建空文件
        emptyFile = tempDir.resolve("empty.zip").toFile();
        emptyFile.createNewFile();

        // 创建非ZIP文件
        nonZipFile = tempDir.resolve("nonzip.txt").toFile();
        try (FileWriter writer = new FileWriter(nonZipFile)) {
            writer.write("This is not a ZIP file");
        }

        // 创建大文件（超过10MB）
        oversizedFile = tempDir.resolve("oversized.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(oversizedFile);
             BufferedOutputStream bos = new BufferedOutputStream(fos)) {
            byte[] largeData = new byte[11 * 1024 * 1024]; // 11MB
            bos.write(largeData);
        }

        // 创建嵌套ZIP文件
        nestedZipFile = createNestedZipFile();

        // 创建路径穿越文件
        pathTraversalFile = createPathTraversalFile();

        // 创建符号链接文件（模拟）
        symlinkFile = createSymlinkFile();

        // 创建深路径文件
        deepPathFile = createDeepPathFile();

        // 创建不安全文件
        unsafeFile = createUnsafeFile();
    }

    // 创建有效的ZIP文件
    private File createValidZipFile() throws IOException {
        File zipFile = tempDir.resolve("valid.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zipFile);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 添加SKILL.md文件，放在valid目录下
            ZipEntry skillMdEntry = new ZipEntry("valid/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String skillMdContent = """
                    ---
                    name: valid
                    description: A valid skill
                    license: MIT
                    allowed-tools: []
                    metadata: {}
                    compatibility: "version1"
                    ---
                    # Skill Description
                    This is a valid skill description.""";
            zos.write(skillMdContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // 添加其他文件
            ZipEntry otherFileEntry = new ZipEntry("README.md");
            zos.putNextEntry(otherFileEntry);
            String otherContent = "# Readme\nThis is readme content.";
            zos.write(otherContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return zipFile;
    }

    // 创建嵌套ZIP文件
    private File createNestedZipFile() throws IOException {
        File nestedZip = tempDir.resolve("nested.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(nestedZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry outerEntry = new ZipEntry("skill-creator.zip");
            zos.putNextEntry(outerEntry);
            String zipContent = "PK0304" + Arrays.toString("This is a nested ZIP file".getBytes(StandardCharsets.UTF_8));
            zos.write(zipContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return nestedZip;
    }

    // 创建路径穿越文件
    private File createPathTraversalFile() throws IOException {
        File traversalFile = tempDir.resolve("traversal.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(traversalFile);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry entry1 = new ZipEntry("normal/file.txt");
            zos.putNextEntry(entry1);
            zos.write("normal content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry entry2 = new ZipEntry("../important/confidential.txt");
            zos.putNextEntry(entry2);
            zos.write("secret content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return traversalFile;
    }

    // 创建符号链接文件（模拟）
    private File createSymlinkFile() throws IOException {
        File symlinkZip = tempDir.resolve("symlink.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(symlinkZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry entry1 = new ZipEntry("normal/file.txt");
            zos.putNextEntry(entry1);
            zos.write("normal content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry entry2 = new ZipEntry("shortcut.lnk");
            zos.putNextEntry(entry2);
            zos.write("shortcut content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return symlinkZip;
    }

    // 创建深路径文件
    private File createDeepPathFile() throws IOException {
        File deepZip = tempDir.resolve("deep.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(deepZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 创建超过10层深的路径
            String deepPath = "level1/level2/level3/level4/level5/level6/level7/level8/level9/level10/level11/file.txt";
            ZipEntry entry = new ZipEntry(deepPath);
            zos.putNextEntry(entry);
            zos.write("deep content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return deepZip;
    }

    // 创建不安全文件
    private File createUnsafeFile() throws IOException {
        File unsafeZip = tempDir.resolve("unsafe.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(unsafeZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 添加无效的SKILL.md文件
            ZipEntry skillMdEntry = new ZipEntry("unsafe/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String invalidSkillMdContent = "---\nname: <script>alert('xss')</script>\ndescription: Invalid skill\n---";
            zos.write(invalidSkillMdContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return unsafeZip;
    }

    // ==================== validateZipFile 方法测试用例 ====================

    /**
     * 测试有效ZIP文件
     */
    @Test
    public void testValidateZipFile_ValidZip() {
        // 创建包含有效SKILL.md的ZIP文件
        File validZip = tempDir.resolve("test-skill.zip").toFile();
        try {
            try (FileOutputStream fos = new FileOutputStream(validZip);
                 ZipOutputStream zos = new ZipOutputStream(fos)) {

                // 创建子目录，并在其中放置SKILL.md文件
                ZipEntry skillMdEntry = new ZipEntry("test-skill/SKILL.md");
                zos.putNextEntry(skillMdEntry);
                String skillMdContent = "---\nname: test-skill\ndescription: Test skill\nlicense: MIT\nallowed-tools: []\nmetadata: {}\ncompatibility: \"version1\"\n---\n# Test Description";
                zos.write(skillMdContent.getBytes(StandardCharsets.UTF_8));
                zos.closeEntry();
            }

            // 验证有效ZIP文件不会抛出异常
            assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(validZip));
        } catch (IOException e) {
            fail("创建测试文件失败: " + e.getMessage());
        }
    }

    /**
     * 测试空文件
     */
    @Test
    public void testValidateZipFile_EmptyFile() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(emptyFile);
        });
        assertEquals(StudioError.ILLEGAL_FILE_TYPE, exception.getErrorCode());
    }

    /**
     * 测试不存在文件
     */
    @Test
    public void testValidateZipFile_NonExistentFile() {
        File nonExistentFile = tempDir.resolve("nonexistent.zip").toFile();
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(nonExistentFile);
        });
        assertEquals(StudioError.ILLEGAL_FILE, exception.getErrorCode());
    }

    /**
     * 测试非ZIP文件
     */
    @Test
    public void testValidateZipFile_NonZipFile() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(nonZipFile);
        });
        assertEquals(StudioError.ILLEGAL_FILE_TYPE, exception.getErrorCode());
    }

    /**
     * 测试文件大小超过限制
     */
    @Test
    public void testValidateZipFile_OversizedFile() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(oversizedFile);
        });
        assertEquals(StudioError.ILLEGAL_FILE_TYPE, exception.getErrorCode());
    }

    /**
     * 测试嵌套ZIP文件
     */
    @Test
    public void testValidateZipFile_NestedZip() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(nestedZipFile);
        });
        assertEquals(StudioError.FILE_NESTED_ZIP, exception.getErrorCode());
    }

    /**
     * 测试路径穿越
     */
    @Test
    public void testValidateZipFile_PathTraversal() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(pathTraversalFile);
        });
        assertEquals(StudioError.INSECURE_PATH, exception.getErrorCode());
    }

    /**
     * 负向：zip 条目名以 "/" 开头（绝对路径）→ 拦截，避免 destDir.resolve 写出临时目录外。
     * 覆盖意见 C：validateZipSecurity 原仅拦截 ".." 相对穿越，未拦截绝对路径条目。
     */
    @Test
    public void testValidateZipFile_AbsolutePathEntry() throws IOException {
        File absZip = tempDir.resolve("absolute-entry.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(absZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry absEntry = new ZipEntry("/etc/passwd");
            zos.putNextEntry(absEntry);
            zos.write("evil".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(absZip));
        assertEquals(StudioError.INSECURE_PATH, exception.getErrorCode());
    }

    /**
     * 负向：zip 条目名为 Windows 盘符绝对路径（如 C:\evil.txt）→ 拦截。
     * 覆盖意见 C：Windows 盘符路径穿越。
     */
    @Test
    public void testValidateZipFile_WindowsDriveAbsolutePathEntry() throws IOException {
        File driveZip = tempDir.resolve("drive-entry.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(driveZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry driveEntry = new ZipEntry("C:\\evil.txt");
            zos.putNextEntry(driveEntry);
            zos.write("evil".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(driveZip));
        assertEquals(StudioError.INSECURE_PATH, exception.getErrorCode());
    }

    /**
     * 测试符号链接
     */
    @Test
    public void testValidateZipFile_Symlink() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(symlinkFile);
        });
        assertEquals(StudioError.UNSAFE_PATH, exception.getErrorCode());
    }

    /**
     * 测试路径深度超过限制
     */
    @Test
    public void testValidateZipFile_DeepPath() {
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(deepPathFile);
        });
        assertEquals(StudioError.ZIP_PATH_TOO_DEEP, exception.getErrorCode());
    }

    /**
     * 测试ZIP条目数超过限制
     */
    @Test
    public void testValidateZipFile_EntryCountExceeded() throws IOException {
        File entryExceededFile = tempDir.resolve("many-entries.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(entryExceededFile);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 创建超过500个条目
            for (int i = 0; i < 501; i++) {
                ZipEntry entry = new ZipEntry("file" + i + ".txt");
                zos.putNextEntry(entry);
                zos.write(("content" + i).getBytes(StandardCharsets.UTF_8));
                zos.closeEntry();
            }
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(entryExceededFile);
        });
        assertEquals(StudioError.ZIP_FILE_COUNT_EXCEED_LIMIT, exception.getErrorCode());
    }

    /**
     * 测试缺少SKILL.md文件
     */
    @Test
    public void testValidateZipFile_MissingSkillMd() throws IOException {
        File missingSkillMd = tempDir.resolve("missing-skill.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(missingSkillMd);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry readmeEntry = new ZipEntry("missing-skill/README.md");
            zos.putNextEntry(readmeEntry);
            zos.write("Readme content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry entry1 = new ZipEntry("docs/file1.txt");
            zos.putNextEntry(entry1);
            zos.write("File content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry entry2 = new ZipEntry("docs/file2.txt");
            zos.putNextEntry(entry2);
            zos.write("File content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(missingSkillMd);
        });
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 测试无效的目录结构
     */
    @Test
    public void testValidateZipFile_InvalidDirectoryStructure() throws IOException {
        File invalidStructure = tempDir.resolve("invalid-structure.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidStructure);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 创建两个子目录，都包含SKILL.md文件
            ZipEntry skillMd1 = new ZipEntry("dir1/SKILL.md");
            zos.putNextEntry(skillMd1);
            zos.write("---\nname: skill1\n---".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd2 = new ZipEntry("dir2/SKILL.md");
            zos.putNextEntry(skillMd2);
            zos.write("---\nname: skill2\n---".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(invalidStructure);
        });
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 测试SKILL.md文件内容为空
     */
    @Test
    public void testValidateZipFile_EmptySkillMd() throws IOException {
        File emptySkillMd = tempDir.resolve("empty-skillmd.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(emptySkillMd);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("empty-skillmd/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            zos.write(new byte[0]);
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(emptySkillMd);
        });
        assertEquals(StudioError.NAME_FIELD_MISSING, exception.getErrorCode());
    }

    /**
     * 测试SKILL.md文件额外字段被忽略（白名单已移除）
     */
    @Test
    public void testValidateZipFile_InvalidSkillMdFields() throws IOException {
        File invalidFields = tempDir.resolve("invalid-fields.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidFields);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("invalid-fields/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String content = "---\nname: invalid-fields\ninvalid-field: not-allowed\nanother-bad-field: value\ndescription: test\n---";
            zos.write(content.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(invalidFields));
        assertNotNull(frontmatter);
        assertEquals("invalid-fields", frontmatter.get("name"));
    }

    /**
     * 测试SKILL.md必填字段缺失
     */
    @Test
    public void testValidateZipFile_MissingRequiredFields() throws IOException {
        File missingFields = tempDir.resolve("missing-fields.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(missingFields);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("missing-fields/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String invalidContent = "---\nlicense: MIT\nmetadata: {}\n---";
            zos.write(invalidContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(missingFields);
        });

        // 应该抛出缺少name或description字段异常
        assertTrue(exception.getErrorCode() == StudioError.NAME_FIELD_MISSING ||
                exception.getErrorCode() == StudioError.DESCRIPTION_FIELD_MISSING);
    }

    /**
     * 测试SKILL.md字段格式无效
     */
    @Test
    public void testValidateZipFile_InvalidNameFormat() throws IOException {
        File invalidName = tempDir.resolve("invalid-name.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidName);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("invalid-name/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String invalidContent = "---\nname: Invalid@Name\ndescription: Valid description\n---";
            zos.write(invalidContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(invalidName);
        });
        assertEquals(StudioError.NAME_FORMAT_MISMATCH, exception.getErrorCode());
    }

    /**
     * 测试SKILL.md字段长度超过限制
     */
    @Test
    public void testValidateZipFile_FieldLengthExceeded() throws IOException {
        File longName = tempDir.resolve("long-name.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(longName);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("long-name/SKILL.md");
            zos.putNextEntry(skillMdEntry);

            // 创建超过64字符的name
            String longNameContent = "---\nname: " + "a".repeat(65) + "\ndescription: Valid description\n---";
            zos.write(longNameContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(longName);
        });
        assertEquals(StudioError.NAME_FORMAT_MISMATCH, exception.getErrorCode());
    }

    /**
     * 测试SKILL.md description字段包含非法字符
     */
    @Test
    public void testValidateZipFile_InvalidDescription() throws IOException {
        File invalidDescription = tempDir.resolve("invalid-desc.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidDescription);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("invalid-desc/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String invalidContent = "---\nname: valid-name\ndescription: Invalid <description> with <tags>\n---";
            zos.write(invalidContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(invalidDescription);
        });
        assertEquals(StudioError.INVALID_CHARACTER, exception.getErrorCode());
    }

    /**
     * 测试SKILL.md compatibility字段长度超过限制
     */
    @Test
    public void testValidateZipFile_CompatibilityLengthExceeded() throws IOException {
        File longCompatibility = tempDir.resolve("long-comp.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(longCompatibility);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("long-comp/SKILL.md");
            zos.putNextEntry(skillMdEntry);

            // 创建超过500字符的compatibility
            String longCompContent = "---\nname: valid-name\ndescription: valid description\ncompatibility: " + "a".repeat(501) + "\n---";
            zos.write(longCompContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(longCompatibility);
        });
        assertEquals(StudioError.COMPATIBILITY_LENGTH_EXCEED, exception.getErrorCode());
    }

    // ==================== validateZipFile 返回 frontmatter 测试用例 ====================

    /**
     * 测试 validateZipFile 直接返回 frontmatter（取代原 getFrontmatter 静态变量方案）
     */
    @Test
    public void testValidateZipFile_ReturnsFrontmatter() {
        // 验证有效 ZIP 文件并直接获取返回的 frontmatter
        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(validZipFile));

        // 验证 frontmatter 不为空且字段正确
        assertNotNull(frontmatter);
        assertEquals("valid", frontmatter.get("name"));
        assertEquals("A valid skill", frontmatter.get("description"));
        assertEquals("MIT", frontmatter.get("license"));
    }

    // ====================  isZipFile 方法测试用例 ====================

    /**
     * 测试有效ZIP文件检测
     */
    @Test
    public void testIsZipFile_ValidZip() {
        assertTrue(ZipValidationUtils.isZipFile(validZipFile));
    }

    /**
     * 测试非ZIP文件检测
     */
    @Test
    public void testIsZipFile_NonZipFile() {
        assertFalse(ZipValidationUtils.isZipFile(nonZipFile));
    }

    /**
     * 测试空文件检测
     */
    @Test
    public void testIsZipFile_EmptyFile() {
        assertFalse(ZipValidationUtils.isZipFile(emptyFile));
    }

    /**
     * 测试不存在文件检测
     */
    @Test
    public void testIsZipFile_NonExistentFile() {
        File nonExistentFile = tempDir.resolve("nonexistent.zip").toFile();
        assertFalse(ZipValidationUtils.isZipFile(nonExistentFile));
    }

    // ==================== 边界条件测试 ====================

    /**
     * 测试文件非合法zip文件
     */
    @Test
    public void testValidateZipFile_InvalidZipStructure() throws IOException {
        File invalidZipFile = tempDir.resolve("invalid.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidZipFile);
             BufferedOutputStream bos = new BufferedOutputStream(fos)) {

            // 写入非 ZIP 文件头的内容（例如普通文本）
            String invalidContent = "This is not a ZIP file";
            bos.write(invalidContent.getBytes(StandardCharsets.UTF_8));
        }

        // 预期触发异常（如不是有效的 ZIP 文件）
        assertThrows(AgentStudioException.class,
                () -> ZipValidationUtils.validateZipFile(invalidZipFile));
    }

    /**
     * 测试多个错误条件同时存在
     */
    @Test
    public void testValidateZipFile_MultipleErrors() throws IOException {
        File multipleErrorsFile = tempDir.resolve("multiple-errors.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(multipleErrorsFile);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            // 路径穿越
            ZipEntry traversalEntry = new ZipEntry("../evil.txt");
            zos.putNextEntry(traversalEntry);
            zos.write("evil content".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // 嵌套ZIP
            ZipEntry nestedEntry = new ZipEntry("inner.zip");
            zos.putNextEntry(nestedEntry);
            zos.write("PK0304nested".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 应该首先捕获路径穿越错误
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(multipleErrorsFile);
        });
        assertEquals(StudioError.INSECURE_PATH, exception.getErrorCode());
    }

    /**
     * 测试正常边界值 - 所有条件都刚好满足限制
     */
    @Test
    public void testValidateZipFile_EdgeCaseAllLimits() throws IOException {
        File edgeCaseFile = tempDir.resolve("edge-skill.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(edgeCaseFile);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            for (int i = 0; i < 499; i++) {
                ZipEntry entry = new ZipEntry("file" + i + ".txt");
                zos.putNextEntry(entry);
                zos.write("small content".getBytes(StandardCharsets.UTF_8));
                zos.closeEntry();
            }

            // 添加SKILL.md
            ZipEntry skillMdEntry = new ZipEntry("edge-skill/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String skillMdContent = "---\nname: edge-skill\ndescription: Edge case skill\nlicense: MIT\nallowed-tools: []\nmetadata: {}\ncompatibility: " +
                    "a".repeat(499) + "\n---\n# Description";
            zos.write(skillMdContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 应该验证通过并返回 frontmatter
        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(edgeCaseFile));

        // 验证 frontmatter
        assertEquals("edge-skill", frontmatter.get("name"));
        assertEquals(499, frontmatter.get("compatibility").toString().length());
    }

    // ==================== 平铺包（flat layout）测试用例 ====================

    /**
     * 平铺包：根级 SKILL.md + 单个附属文件 → 校验通过
     */
    @Test
    public void testValidateZipFile_FlatLayout_WithMetaFile() throws IOException {
        File zip = tempDir.resolve("flat-meta.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry meta = new ZipEntry("_meta.json");
            zos.putNextEntry(meta);
            zos.write("{\"version\":\"1.0\"}".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: flat-skill\ndescription: A flat skill\nlicense: MIT\n---\n# Flat Skill".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("flat-skill", frontmatter.get("name"));
        assertEquals("A flat skill", frontmatter.get("description"));
    }

    /**
     * 平铺包：根级 SKILL.md + 多个附属子目录（scripts/ styles/ tests/）→ 校验通过
     */
    @Test
    public void testValidateZipFile_FlatLayout_MultipleSubFolders() throws IOException {
        File zip = tempDir.resolve("flat-multi.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry script = new ZipEntry("scripts/run.py");
            zos.putNextEntry(script);
            zos.write("print('hi')".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry style = new ZipEntry("styles/main.css");
            zos.putNextEntry(style);
            zos.write("body{}".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry test = new ZipEntry("tests/test.py");
            zos.putNextEntry(test);
            zos.write("assert True".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: multi-flat\ndescription: multi folder flat\n---\n# Multi".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("multi-flat", frontmatter.get("name"));
    }

    /**
     * 平铺包：zip 文件名与 name 字段不一致 → 校验通过（不比对 zip 文件名）
     */
    @Test
    public void testValidateZipFile_FlatLayout_ZipNameMismatch() throws IOException {
        // zip 文件名是 random-name.zip，但 SKILL.md name 是 my-flat-skill
        File zip = tempDir.resolve("random-name.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: my-flat-skill\ndescription: name mismatch test\n---\n# Skill".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 校验通过：平铺结构不比对 zip 文件名
        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertEquals("my-flat-skill", frontmatter.get("name"));
    }

    /**
     * 平铺包：含中文文件名 → 校验通过
     */
    @Test
    public void testValidateZipFile_FlatLayout_ChineseFilename() throws IOException {
        File zip = tempDir.resolve("flat-chinese.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry script = new ZipEntry("脚本/run.py");
            zos.putNextEntry(script);
            zos.write("print('中文')".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: chinese-flat\ndescription: 中文文件名测试\n---\n# 中文".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertEquals("chinese-flat", frontmatter.get("name"));
    }

    /**
     * 负向：平铺包根级 + 子目录同时含 SKILL.md → 抛 FILES_NUMBER_DOES_NOT_MATCH
     * 覆盖 §3.2.1 新增校验
     */
    @Test
    public void testValidateZipFile_FlatLayout_RootAndChildBothHaveSkillMd() throws IOException {
        File zip = tempDir.resolve("flat-dup.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry rootSkillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(rootSkillMd);
            zos.write("---\nname: root-skill\ndescription: root\n---\n# Root".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry subSkillMd = new ZipEntry("subdir/SKILL.md");
            zos.putNextEntry(subSkillMd);
            zos.write("---\nname: sub-skill\ndescription: sub\n---\n# Sub".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(zip));
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 平铺包：根级带 frontmatter 的 SKILL.md + 子目录不带 frontmatter 的同名 SKILL.md → 校验通过
     * 覆盖 ima-skills 等多模块聚合包场景（子目录的 SKILL.md 只是普通说明文档）
     */
    @Test
    public void testValidateZipFile_FlatLayout_RootSkillMdWithChildPlainSkillMd() throws IOException {
        File zip = tempDir.resolve("flat-multi-module.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            // 根级 SKILL.md — 带 frontmatter（真正的 skill 定义）
            ZipEntry rootSkillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(rootSkillMd);
            zos.write("---\nname: ima-skill\ndescription: IMA skill with sub-module docs\n---\n# IMA Skill".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // 子目录 SKILL.md — 不带 frontmatter（普通说明文档）
            ZipEntry notesSkillMd = new ZipEntry("notes/SKILL.md");
            zos.putNextEntry(notesSkillMd);
            zos.write("# Notes Module\nPlain markdown doc, not a skill definition.".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry kbSkillMd = new ZipEntry("knowledge-base/SKILL.md");
            zos.putNextEntry(kbSkillMd);
            zos.write("# Knowledge Base Module\nAlso a plain markdown doc.".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // 附属脚本
            ZipEntry script = new ZipEntry("ima_api.cjs");
            zos.putNextEntry(script);
            zos.write("// api script".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("ima-skill", frontmatter.get("name"));
        assertEquals("IMA skill with sub-module docs", frontmatter.get("description"));
    }

    /**
     * block scalar: description: | 多行内容（literal，保留换行语义转为描述）
     */
    @Test
    public void testValidateZipFile_BlockScalarLiteral() throws IOException {
        File zip = tempDir.resolve("block-literal.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            String content = "---\nname: block-skill\ndescription: |\n  First paragraph.\n  Second paragraph.\n---\n# Skill";
            zos.write(content.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("block-skill", frontmatter.get("name"));
        String desc = frontmatter.get("description").toString();
        assertTrue(desc.contains("First paragraph."), "description should contain first paragraph");
        assertTrue(desc.contains("Second paragraph."), "description should contain second paragraph");
    }

    /**
     * block scalar: description: > 多行内容（folded，换行合并为空格）
     */
    @Test
    public void testValidateZipFile_BlockScalarFolded() throws IOException {
        File zip = tempDir.resolve("block-folded.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            String content = "---\nname: folded-skill\ndescription: >\n  Line one.\n  Line two.\n---\n# Skill";
            zos.write(content.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("folded-skill", frontmatter.get("name"));
        String desc = frontmatter.get("description").toString();
        assertTrue(desc.contains("Line one."), "description should contain line one");
        assertTrue(desc.contains("Line two."), "description should contain line two");
    }

    /**
     * block scalar: description: >- 带 chomping indicator
     */
    @Test
    public void testValidateZipFile_BlockScalarChompingIndicator() throws IOException {
        File zip = tempDir.resolve("block-chomp.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            String content = "---\nname: chomp-skill\ndescription: >-\n  Stripped content here.\n---\n# Skill";
            zos.write(content.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("chomp-skill", frontmatter.get("name"));
        assertEquals("Stripped content here.", frontmatter.get("description"));
    }

    /**
     * block scalar: CRLF 换行下空行不截断 block 内容
     */
    @Test
    public void testValidateZipFile_BlockScalarCRLF() throws IOException {
        File zip = tempDir.resolve("block-crlf.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            String content = "---\r\nname: crlf-skill\r\ndescription: |\r\n  Para one.\r\n\r\n  Para two.\r\n---\r\n# Skill";
            zos.write(content.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertNotNull(frontmatter);
        assertEquals("crlf-skill", frontmatter.get("name"));
        String desc = frontmatter.get("description").toString();
        assertTrue(desc.contains("Para one."), "description should contain para one");
        assertTrue(desc.contains("Para two."), "description should contain para two after blank line");
    }

    /**
     * 负向：平铺包多个子目录同时含 SKILL.md（无根级 SKILL.md）→ 抛 FILES_NUMBER_DOES_NOT_MATCH
     */
    @Test
    public void testValidateZipFile_MultipleSubFoldersWithSkillMd() throws IOException {
        File zip = tempDir.resolve("multi-sub-skillmd.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry s1 = new ZipEntry("dir1/SKILL.md");
            zos.putNextEntry(s1);
            zos.write("---\nname: skill1\ndescription: s1\n---\n# s1".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry s2 = new ZipEntry("dir2/SKILL.md");
            zos.putNextEntry(s2);
            zos.write("---\nname: skill2\ndescription: s2\n---\n# s2".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(zip));
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 负向：单文件夹结构但根级有额外非空目录（assets/ + my-skill/SKILL.md）
     * → 抛 FILES_NUMBER_DOES_NOT_MATCH。
     * 覆盖意见 Medium Priority #415：避免详情页 sortTree 按字母序取 innerData[0]=assets/，
     * openSkillMd 在 assets/SKILL.md 找不到文件而无法自动打开 SKILL.md。
     */
    @Test
    public void testValidateZipFile_SingleFolderWithExtraRootDir() throws IOException {
        File zip = tempDir.resolve("extra-root-dir.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            // 额外的非空目录（字母序在 my-skill 之前）
            ZipEntry asset = new ZipEntry("assets/style.css");
            zos.putNextEntry(asset);
            zos.write("body{}".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // 含 SKILL.md 的目录
            ZipEntry skillMd = new ZipEntry("my-skill/SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: my-skill\ndescription: extra\n---\n# Extra".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(zip));
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 负向：单文件夹包中 SKILL.md 位于深层子目录 a/b/SKILL.md
     * → 结构校验阶段拦截：SKILL.md 所在目录不是 baseDir 的直接子目录
     * （rel.getNameCount() != 1），抛 FILES_NUMBER_DOES_NOT_MATCH。
     * 覆盖意见 G：禁止 a/b/SKILL.md 通过，避免生成不符合 {name}/SKILL.md 规范的制品。
     */
    @Test
    public void testValidateZipFile_DeepSkillMd_NameMismatch() throws IOException {
        File zip = tempDir.resolve("deep-skillmd.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry deep = new ZipEntry("a/b/SKILL.md");
            zos.putNextEntry(deep);
            zos.write("---\nname: my-skill\ndescription: deep\n---\n# Deep".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.validateZipFile(zip));
        assertEquals(StudioError.FILES_NUMBER_DOES_NOT_MATCH, exception.getErrorCode());
    }

    /**
     * 负向：平铺包根级存在与 skillName 同名的<b>文件</b>（非目录）
     * → repackIfFlat 在 Files.createDirectories 时抛 FileAlreadyExistsException
     * → 显式捕获并返回 NAME_FORMAT_MISMATCH（而非泛化的 RESOURCE_READER_ERROR）。
     * 覆盖意见 H：避免错误码误导排错。
     */
    @Test
    public void testRepackIfFlat_FlatLayout_RootConflictFileName() throws IOException {
        File zip = tempDir.resolve("repack-conflict.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            // 根级同名文件（非目录）
            ZipEntry conflict = new ZipEntry("my-skill");
            zos.putNextEntry(conflict);
            zos.write("not a directory".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: my-skill\ndescription: conflict\n---\n# Conflict".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 先校验通过（validateDirectoryStructure 不拦截同名文件）
        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertEquals("my-skill", frontmatter.get("name"));

        // 重打包阶段应抛 NAME_FORMAT_MISMATCH
        AgentStudioException exception = assertThrows(AgentStudioException.class, () ->
                ZipValidationUtils.repackIfFlat(zip, "my-skill"));
        assertEquals(StudioError.NAME_FORMAT_MISMATCH, exception.getErrorCode());
    }

    /**
     * 边缘场景：单字符 skillName（如 "a"）→ tempPrefix = "a-" 长度 2 < 3
     * → repackIfFlat 补足到 "skill-a-" 后正常创建临时文件，重打包成功。
     * 覆盖意见 Medium Priority #123：Files.createTempFile 前缀长度要求 ≥ 3 字符。
     */
    @Test
    public void testRepackIfFlat_FlatLayout_SingleCharName() throws IOException {
        File zip = tempDir.resolve("repack-single-char.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: a\ndescription: single char\n---\n# Single".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        File repacked = ZipValidationUtils.repackIfFlat(zip, "a");
        try {
            assertNotNull(repacked);
            assertTrue(repacked.exists());
            List<String> entries = listZipEntries(repacked);
            assertTrue(entries.contains("a/SKILL.md"));
        } finally {
            if (repacked != zip && repacked.exists()) {
                repacked.delete();
            }
        }
    }

    // ==================== repackIfFlat 方法测试用例 ====================

    /**
     * 平铺包重打包：输入根级 SKILL.md + _meta.json，输出 zip 解压后为 {name}/SKILL.md + {name}/_meta.json
     */
    @Test
    public void testRepackIfFlat_FlatLayout() throws IOException {
        File zip = tempDir.resolve("repack-flat.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry meta = new ZipEntry("_meta.json");
            zos.putNextEntry(meta);
            zos.write("{\"v\":\"1\"}".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: repack-skill\ndescription: repack test\n---\n# Repack".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        File repacked = ZipValidationUtils.repackIfFlat(zip, "repack-skill");
        try {
            assertNotNull(repacked);
            assertTrue(repacked.exists());
            // 验证解压后条目为 {name}/SKILL.md + {name}/_meta.json
            List<String> entries = listZipEntries(repacked);
            assertTrue(entries.contains("repack-skill/SKILL.md"));
            assertTrue(entries.contains("repack-skill/_meta.json"));
            // 不应有根级 SKILL.md
            assertFalse(entries.contains("SKILL.md"));
        } finally {
            if (repacked != zip && repacked.exists()) {
                repacked.delete();
            }
        }
    }

    /**
     * 多文件夹平铺包重打包：输出 {name}/SKILL.md + {name}/scripts/run.py
     */
    @Test
    public void testRepackIfFlat_MultiFolderFlat() throws IOException {
        File zip = tempDir.resolve("repack-multi.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry script = new ZipEntry("scripts/run.py");
            zos.putNextEntry(script);
            zos.write("print(1)".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: multi-repack\ndescription: multi\n---\n# Multi".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        File repacked = ZipValidationUtils.repackIfFlat(zip, "multi-repack");
        try {
            List<String> entries = listZipEntries(repacked);
            assertTrue(entries.contains("multi-repack/SKILL.md"));
            assertTrue(entries.contains("multi-repack/scripts/run.py"));
        } finally {
            if (repacked != zip && repacked.exists()) {
                repacked.delete();
            }
        }
    }

    /**
     * 重打包后中文文件名无乱码
     */
    @Test
    public void testRepackIfFlat_ChineseFilename() throws IOException {
        File zip = tempDir.resolve("repack-chinese.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry script = new ZipEntry("脚本/run.py");
            zos.putNextEntry(script);
            zos.write("print('中文')".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: chinese-repack\ndescription: 中文\n---\n# 中文".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        File repacked = ZipValidationUtils.repackIfFlat(zip, "chinese-repack");
        try {
            List<String> entries = listZipEntries(repacked);
            assertTrue(entries.contains("chinese-repack/SKILL.md"));
            assertTrue(entries.contains("chinese-repack/脚本/run.py"));
        } finally {
            if (repacked != zip && repacked.exists()) {
                repacked.delete();
            }
        }
    }

    /**
     * 单文件夹包（回归）：repackIfFlat 返回原 zipFile（引用相等 ==）
     */
    @Test
    public void testRepackIfFlat_SingleFolder_ReturnsOriginal() throws IOException {
        File zip = tempDir.resolve("repack-single.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry skillMd = new ZipEntry("my-skill/SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: my-skill\ndescription: single\n---\n# Single".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 单文件夹结构：返回值应与入参引用相等
        File result = ZipValidationUtils.repackIfFlat(zip, "my-skill");
        assertSame(zip, result);
    }

    /**
     * 边缘场景：平铺包根级存在与 skillName 同名子目录（SKILL.md + my-skill/helper.py，name=my-skill）
     * 预期：校验通过；重打包后为 my-skill/SKILL.md + my-skill/helper.py
     */
    @Test
    public void testRepackIfFlat_FlatLayout_WithSameNameSubFolder() throws IOException {
        File zip = tempDir.resolve("repack-edge.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(zip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {
            ZipEntry helper = new ZipEntry("my-skill/helper.py");
            zos.putNextEntry(helper);
            zos.write("helper".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            ZipEntry skillMd = new ZipEntry("SKILL.md");
            zos.putNextEntry(skillMd);
            zos.write("---\nname: my-skill\ndescription: edge\n---\n# Edge".getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        // 先验证校验通过
        Map<String, Object> frontmatter = assertDoesNotThrow(() -> ZipValidationUtils.validateZipFile(zip));
        assertEquals("my-skill", frontmatter.get("name"));

        // 重打包后为 my-skill/SKILL.md + my-skill/helper.py
        File repacked = ZipValidationUtils.repackIfFlat(zip, "my-skill");
        try {
            List<String> entries = listZipEntries(repacked);
            assertTrue(entries.contains("my-skill/SKILL.md"));
            assertTrue(entries.contains("my-skill/helper.py"));
        } finally {
            if (repacked != zip && repacked.exists()) {
                repacked.delete();
            }
        }
    }

    // ==================== 并发测试 ====================

    /**
     * 并发调用 validateZipFile：N 个线程并发导入 N 个不同 skill，
     * 每个线程拿到的 frontmatter 与各自包内 SKILL.md 一致
     * 覆盖 §3.2.4 frontmatter 静态变量线程安全修复
     */
    @Test
    public void testValidateZipFile_ConcurrentThreads_GetCorrectFrontmatter() throws Exception {
        int threadCount = 8;
        ExecutorService pool = Executors.newFixedThreadPool(threadCount);
        try {
            // 为每个线程创建一个独立的平铺包，name 各不相同
            ConcurrentHashMap<Integer, String> actualNames = new ConcurrentHashMap<>();
            List<Future<Void>> futures = new ArrayList<>();
            for (int i = 0; i < threadCount; i++) {
                final int idx = i;
                final String skillName = "skill-" + idx;
                Callable<Void> task = () -> {
                    File zip = tempDir.resolve("concurrent-" + idx + "-" + UUID.randomUUID() + ".zip").toFile();
                    try (FileOutputStream fos = new FileOutputStream(zip);
                         ZipOutputStream zos = new ZipOutputStream(fos)) {
                        ZipEntry skillMd = new ZipEntry("SKILL.md");
                        zos.putNextEntry(skillMd);
                        zos.write(("---\nname: " + skillName + "\ndescription: concurrent " + idx + "\n---\n# " + skillName)
                                .getBytes(StandardCharsets.UTF_8));
                        zos.closeEntry();
                    }

                    // 模拟并发：多线程同时调用 validateZipFile
                    Map<String, Object> frontmatter = ZipValidationUtils.validateZipFile(zip);
                    actualNames.put(idx, frontmatter.get("name").toString());

                    // 清理
                    zip.delete();
                    return null;
                };
                futures.add(pool.submit(task));
            }

            // 等待全部完成，任意一个失败立即抛出
            for (Future<Void> f : futures) {
                f.get();
            }

            // 断言每个线程拿到各自的 name
            for (int i = 0; i < threadCount; i++) {
                assertEquals("skill-" + i, actualNames.get(i),
                        "线程 " + i + " 拿到了错误的 frontmatter（线程安全回归）");
            }
        } finally {
            pool.shutdown();
            assertTrue(pool.awaitTermination(30, TimeUnit.SECONDS));
        }
    }

    // ==================== 辅助方法 ====================

    /**
     * 列出 zip 文件中所有条目名（用于重打包结果断言）
     */
    private List<String> listZipEntries(File zipFile) throws IOException {
        List<String> result = new ArrayList<>();
        try (ZipFile zf = new ZipFile(zipFile)) {
            Enumeration<? extends ZipEntry> entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                if (!entry.isDirectory()) {
                    result.add(entry.getName());
                }
            }
        } catch (java.util.zip.ZipException e) {
            // GBK 回退
            try (ZipFile zf = new ZipFile(zipFile, java.nio.charset.Charset.forName("GBK"))) {
                Enumeration<? extends ZipEntry> entries = zf.entries();
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    if (!entry.isDirectory()) {
                        result.add(entry.getName());
                    }
                }
            }
        }
        return result;
    }

}

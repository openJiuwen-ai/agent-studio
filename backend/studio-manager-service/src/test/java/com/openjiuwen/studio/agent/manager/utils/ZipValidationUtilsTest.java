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
import java.util.Arrays;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
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
     * 测试SKILL.md文件无效字段
     */
    @Test
    public void testValidateZipFile_InvalidSkillMdFields() throws IOException {
        File invalidFields = tempDir.resolve("invalid-fields.zip").toFile();
        try (FileOutputStream fos = new FileOutputStream(invalidFields);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            ZipEntry skillMdEntry = new ZipEntry("invalid-fields/SKILL.md");
            zos.putNextEntry(skillMdEntry);
            String invalidContent = "---\nname: test\ninvalid-field: not-allowed\nanother-bad-field: value\n---";
            zos.write(invalidContent.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            ZipValidationUtils.validateZipFile(invalidFields);
        });
        assertEquals(StudioError.SKILL_MD_INVALID_FIELD, exception.getErrorCode());
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

    // ==================== frontmatter 返回值测试用例 ====================

    /**
     * 测试获取frontmatter
     */
    @Test
    public void testValidateZipFile_ReturnsFrontmatter() {
        Map<String, Object> frontmatter = ZipValidationUtils.validateZipFile(validZipFile);
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

        // 应该验证通过并返回frontmatter
        Map<String, Object> frontmatter = ZipValidationUtils.validateZipFile(edgeCaseFile);
        assertEquals("edge-skill", frontmatter.get("name"));
        assertEquals(499, frontmatter.get("compatibility").toString().length());
    }

}

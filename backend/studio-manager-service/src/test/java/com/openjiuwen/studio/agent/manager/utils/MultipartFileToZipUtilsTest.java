/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@MockitoSettings(strictness = Strictness.LENIENT)
class MultipartFileToZipUtilsTest {

    private Path testDir;
    private Path targetDir;

    @BeforeEach
    void setUp() throws IOException {
        testDir = Files.createTempDirectory("MultipartFileToZipUtilsTest_");
        targetDir = Files.createTempDirectory("MultipartFileToZipTarget_");
        testDir.toFile().deleteOnExit();
        targetDir.toFile().deleteOnExit();
    }

    @Test
    void testConvertToZipFile_withValidMultipartFileAndTargetDir_returnZipFile() throws Exception {
        // Arrange
        String originalFilename = "test.zip";
        byte[] content = "test content".getBytes(StandardCharsets.UTF_8);
        String expectedContent = new String(content, StandardCharsets.UTF_8);

        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", content);

        File resultFile = MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        assertNotNull(resultFile, "Converted file should not be null");
        assertTrue(resultFile.exists(), "Converted file should exist");
        assertTrue(resultFile.getName().endsWith(originalFilename),
                "Converted filename should end with original filename");
        String actualContent = new String(Files.readAllBytes(resultFile.toPath()));
        assertEquals(expectedContent, actualContent, "File content should be correct");
        assertTrue(resultFile.getParentFile().getAbsolutePath().contains(targetDir.toString()),
                "File should be saved in specified target directory");
    }

    @Test
    void testConvertToZipFile_withValidMultipartFileToDefaultDir_returnZipFile() throws Exception {
        // Arrange
        String originalFilename = "test.zip";
        byte[] content = "test content".getBytes(StandardCharsets.UTF_8);
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", content);

        File resultFile = MultipartFileToZipUtils.convertToZipFile(multipartFile);
        assertNotNull(resultFile, "Converted file should not be null");
        assertTrue(resultFile.exists(), "Converted file should exist");
        assertTrue(resultFile.getName().endsWith(originalFilename),
                "Converted filename should end with original filename");
    }

    @Test
    void testConvertToZipFile_withMultipartFileWithoutExtension_returnFile() throws Exception {
        // Arrange
        String originalFilename = "testfile";
        byte[] content = "test content".getBytes(StandardCharsets.UTF_8);
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/octet-stream", content);

        File resultFile = MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());

        assertNotNull(resultFile, "Converted file should not be null");
        assertTrue(resultFile.exists(), "Converted file should exist");
        assertTrue(resultFile.getName().endsWith(originalFilename),
                "Converted filename should end with original filename");
        String actualContent = new String(Files.readAllBytes(resultFile.toPath()));
        assertEquals(new String(content, StandardCharsets.UTF_8), actualContent, "File content should be correct");
    }

    @Test
    void testConvertToZipFile_withEmptyContent_returnEmptyZipFile() throws Exception {
        // Arrange
        String originalFilename = "empty.zip";
        byte[] content = "".getBytes(StandardCharsets.UTF_8);

        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", content);

        // Act
        File resultFile = MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        assertNotNull(resultFile, "Converted file should not be null");
        assertTrue(resultFile.exists(), "Converted file should exist");
        assertTrue(resultFile.getName().endsWith(originalFilename),
                "Converted filename should end with original filename");
        assertEquals(0, resultFile.length(), "Empty file should be created successfully");
    }

    @Test
    void testConvertToZipFile_withLargeContent_returnLargeZipFile() throws Exception {
        // Arrange
        String originalFilename = "large.zip";
        StringBuilder largeContent = new StringBuilder();

        for (int i = 0; i < 10000; i++) {
            largeContent.append("This is line ").append(i).append(" content.\n");
        }
        byte[] content = largeContent.toString().getBytes(StandardCharsets.UTF_8);
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", content);

        File resultFile = MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        assertNotNull(resultFile, "Converted file should not be null");
        assertTrue(resultFile.exists(), "Converted file should exist");
        assertEquals(content.length, resultFile.length(), "Large file should be saved correctly");
    }

    @Test
    void testConvertToZipFile_withInvalidTargetDir_throwAgentStudioException() {
        // Arrange
        String originalFilename = "test.zip";
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", "content".getBytes(StandardCharsets.UTF_8));

        // Use an invalid path
        String invalidPath = "C:\\invalid|path|with|pipes";
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, invalidPath);
        });
        assertEquals(StudioError.ILLEGAL_FILE, exception.getErrorCode(),
                "Exception should be ILLEGAL_FILE");
    }

    @Test
    void testConvertToZipFile_withNullMultipartFile_throwNullPointerException() {
        // Arrange
        MultipartFile nullMultipartFile = null;
        assertThrows(NullPointerException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(null, targetDir.toString());
        });
    }

    @Test
    void testConvertToZipFile_withNullFilename_throwAgentStudioException() throws Exception {
        // Arrange
        MultipartFile multipartFile = mock(MultipartFile.class);
        when(multipartFile.getOriginalFilename()).thenReturn(null);
        when(multipartFile.getInputStream()).thenReturn(new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8)));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.ILLEGAL_FILE, exception.getErrorCode(),
                "Exception should be ILLEGAL_FILE");
    }

    @Test
    void testConvertToZipFile_withIOExceptionDuringTransfer_throwAgentStudioException() throws Exception {
        String originalFilename = "test.zip";

        // a Create MockMultipartFile that throws IOException
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", "content".getBytes(StandardCharsets.UTF_8)) {
            @Override
            public void transferTo(File dest) throws IOException {
                // Simulate IO exception during transfer
                throw new IOException("Simulated IO exception during transfer");
            }
        };

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.IO_ERROR, exception.getErrorCode(),
                "Exception should be IO_ERROR");
    }

    @Test
    void testConvertToZipFile_withPathTraversalDotDot_throwAgentStudioException() {
        MockMultipartFile multipartFile = new MockMultipartFile("file", "../../../tmp/evil.zip",
                "application/zip", "content".getBytes(StandardCharsets.UTF_8));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.ILLEGAL_FILE_NAME, exception.getErrorCode(),
                "Exception should be ILLEGAL_FILE_NAME for path traversal with ..");
    }

    @Test
    void testConvertToZipFile_withBackslashInFilename_throwAgentStudioException() {
        MockMultipartFile multipartFile = new MockMultipartFile("file", "path\\evil.zip",
                "application/zip", "content".getBytes(StandardCharsets.UTF_8));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.ILLEGAL_FILE_NAME, exception.getErrorCode(),
                "Exception should be ILLEGAL_FILE_NAME for backslash in filename");
    }

    @Test
    void testConvertToZipFile_withSlashInFilename_throwAgentStudioException() {
        MockMultipartFile multipartFile = new MockMultipartFile("file", "path/evil.zip",
                "application/zip", "content".getBytes(StandardCharsets.UTF_8));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.ILLEGAL_FILE_NAME, exception.getErrorCode(),
                "Exception should be ILLEGAL_FILE_NAME for slash in filename");
    }

    @Test
    void testConvertToZipFile_withInterruptedIO_throwAgentStudioException() throws Exception {
        // Arrange
        String originalFilename = "test.zip";

        // Create MockMultipartFile with null filename to simulate unexpected scenario
        MockMultipartFile multipartFile = new MockMultipartFile("file", originalFilename,
                "application/zip", "content".getBytes(StandardCharsets.UTF_8)) {
            @Override
            public String getOriginalFilename() {
                // Return null to trigger UNEXPECTED_ERROR case in the main method
                return null;
            }
        };

        // Act & Assert
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            MultipartFileToZipUtils.convertToZipFile(multipartFile, targetDir.toString());
        });
        assertEquals(StudioError.ILLEGAL_FILE, exception.getErrorCode(), "Exception should be ILLEGAL_FILE");
    }

    @AfterEach
    void tearDown() {
        // Clean up test directories and files
        if (testDir != null && Files.exists(testDir)) {
            try (Stream<Path> paths = Files.walk(testDir)) {
                paths.sorted((a, b) -> -a.compareTo(b)).forEach(path -> {
                    try {
                        Files.deleteIfExists(path);
                    } catch (IOException e) {
                        throw new AgentStudioException(StudioError.IO_ERROR);
                    }
                });
            } catch (IOException e) {
                throw new AgentStudioException(StudioError.IO_ERROR);
            }
        }

        if (targetDir != null && Files.exists(targetDir)) {
            try (Stream<Path> paths = Files.walk(targetDir)) {
                paths.sorted((a, b) -> -a.compareTo(b)).forEach(path -> {
                    try {
                        Files.deleteIfExists(path);
                    } catch (IOException e) {
                        throw new AgentStudioException(StudioError.IO_ERROR);
                    }
                });
            } catch (IOException e) {
                throw new AgentStudioException(StudioError.IO_ERROR);
            }
        }
    }
}

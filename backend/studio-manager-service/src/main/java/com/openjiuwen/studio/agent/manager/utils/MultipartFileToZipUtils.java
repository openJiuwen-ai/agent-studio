/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.UUID;

/**
 * MultipartFile 转 ZIP 文件工具类
 *
 */
@Slf4j
public class MultipartFileToZipUtils {

    /**
     * 将 MultipartFile 转换为 ZIP 文件
     *
     * @param multipartFile 上传的 ZIP 文件（MultipartFile 格式）
     * @param targetDir     ZIP 文件保存的目标目录
     * @return 生成的 ZIP 文件对象
     */
    public static File convertToZipFile(MultipartFile multipartFile, String targetDir) {
        // 验证目标目录
        File dir = new File(targetDir);

        // 检查目录是否存在且为目录
        if (!dir.exists()) {
            log.error("Target directory does not exist: {}", targetDir);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        // 检查是否为目录而不是文件
        if (!dir.isDirectory()) {
            log.error("Target path is not a directory: {}", targetDir);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        // 检查目录是否可写
        if (!dir.canWrite()) {
            log.error("Target directory is not writable: {}", targetDir);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        // 创建目标 ZIP 文件
        String originalFilename = multipartFile.getOriginalFilename();
        if (originalFilename == null || originalFilename.isEmpty()) {
            log.error("The original file name cannot be empty.");
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        // 校验文件名不含路径穿越字符
        if (originalFilename.contains("..") || originalFilename.contains("\\")
                || originalFilename.contains("/")) {
            log.error("The file name contains path traversal characters: {}", originalFilename);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        // 构建目标 ZIP 文件路径（使用唯一文件名避免并发冲突）
        String uniqueFileName = UUID.randomUUID() + "_" + originalFilename;
        File zipFile = new File(dir, uniqueFileName);

        try {
            // 将 MultipartFile 写入目标 ZIP 文件
            multipartFile.transferTo(zipFile);
        } catch (IOException e) {
            log.error("Failed to write file to disk: {}", zipFile.getAbsolutePath(), e);
            throw new AgentStudioException(StudioError.IO_ERROR);
        }

        return zipFile;
    }

    /**
     * 将 MultipartFile 转换为 ZIP 文件（默认保存在系统临时目录）
     *
     * @param multipartFile 上传的 ZIP 文件（MultipartFile 格式）
     * @return 生成的 ZIP 文件对象
     */
    public static File convertToZipFile(MultipartFile multipartFile) {
        return convertToZipFile(multipartFile, System.getProperty("java.io.tmpdir"));
    }
}

/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * #1653/#1722：客户端正常拒绝 handler 须 log.warn，不得 log.error（对齐 BindException）。
 */
class ClientRejectLogLevelContractTest {

    @Test
    void n1_n2_n3_handlers_use_warn_not_error() throws Exception {
        Path source = Path.of("src/main/java/com/openjiuwen/studio/agent/manager/exception/MgGlobalExceptionHandler.java");
        String text = Files.readString(source, StandardCharsets.UTF_8);

        assertTrue(text.contains("log.warn(\"throw MethodArgumentNotValidException:"));
        assertTrue(text.contains("log.warn(\"throw ConstraintViolationException:"));
        assertTrue(text.contains("log.warn(\"NoResourceFoundException:"));
        assertTrue(text.contains("log.warn(\"MaxUploadSizeExceededException:"));
        assertTrue(text.contains("log.warn(\"BindException:"));

        assertFalse(text.contains("log.error(\"throw MethodArgumentNotValidException:"));
        assertFalse(text.contains("log.error(\"throw ConstraintViolationException:"));
        assertFalse(text.contains("log.error(\"NoResourceFoundException:"));
        assertFalse(text.contains("log.error(\"MaxUploadSizeExceededException:"));
    }
}

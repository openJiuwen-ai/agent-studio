/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.common.storage;

import com.obs.services.ObsClient;
import com.obs.services.exception.ObsException;
import com.obs.services.model.ObsObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

/**
 * ObsFileStoreImpl.read / readOrNull 测试：
 * read：404→抛 OBS_FAILED、5xx→抛 OBS_FAILED、正常→内容（read 对 404 不降级 null，避免调用方解引用 NPE）；
 * readOrNull：404→null（仅此 404 语义化为 null，收敛到发布元数据读取）、5xx→抛 OBS_FAILED、正常→内容。
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class ObsFileStoreImplTest {

    @Mock
    private ObsClient obsClient;

    private ObsFileStoreImpl fileStore;

    @BeforeEach
    void setUp() {
        // path 含 "/" 时 splitPath 用前缀作 bucket，不依赖 obsConfig.getBucket()。
        fileStore = new ObsFileStoreImpl(null);
        ReflectionTestUtils.setField(fileStore, "obsClient", obsClient);
    }

    /** read: OBS 404 → 抛 OBS_FAILED（不降级 null，404 在多数调用方是数据不一致故障；read 不区分 errorCode）。 */
    @Test
    void read_obsNotFound404_throwsObsFailed() {
        when(obsClient.getObject(eq("bucket"), eq("missing-key")))
            .thenThrow(obsException(404, "NoSuchKey"));
        AgentStudioException thrown = assertThrows(AgentStudioException.class,
            () -> fileStore.read("bucket/missing-key"));
        assertEquals(StudioError.OBS_FAILED, thrown.getErrorCode(),
            "read 404 应抛 OBS_FAILED，不降级 null（避免调用方解引用 NPE）");
    }

    /** read: 真实 OBS 故障（非 404，如 500）→ 抛 OBS_FAILED。 */
    @Test
    void read_obsFailure500_throwsObsFailed() {
        when(obsClient.getObject(eq("bucket"), eq("key")))
            .thenThrow(obsException(500, null));
        AgentStudioException thrown = assertThrows(AgentStudioException.class,
            () -> fileStore.read("bucket/key"));
        assertEquals(StudioError.OBS_FAILED, thrown.getErrorCode(),
            "真实 OBS 故障应抛 OBS_FAILED(500)，不降级为 null");
    }

    /** read: 正常读取 → 返回内容。 */
    @Test
    void read_success_returnsContent() {
        ObsObject obj = new ObsObject();
        obj.setObjectContent(new ByteArrayInputStream("hello".getBytes(StandardCharsets.UTF_8)));
        when(obsClient.getObject(eq("bucket"), eq("key"))).thenReturn(obj);
        assertEquals("hello", fileStore.read("bucket/key"));
    }

    /** readOrNull: OBS 404 + NoSuchKey（对象不存在=未发布）→ 返回 null（仅此语义化为 null，收敛到发布元数据读取）。 */
    @Test
    void readOrNull_obsNotFound404_returnsNull() {
        when(obsClient.getObject(eq("bucket"), eq("missing-key")))
            .thenThrow(obsException(404, "NoSuchKey"));
        assertNull(fileStore.readOrNull("bucket/missing-key"),
            "readOrNull 404+NoSuchKey 应返回 null（对象不存在=业务语义），不抛 500");
    }

    /** readOrNull: OBS 404 + NoSuchBucket（桶缺失/配置错）→ 抛 OBS_FAILED（不误判为未发布，避免掩盖真实 OBS 故障）。 */
    @Test
    void readOrNull_noSuchBucket404_throwsObsFailed() {
        when(obsClient.getObject(eq("bucket"), eq("key")))
            .thenThrow(obsException(404, "NoSuchBucket"));
        AgentStudioException thrown = assertThrows(AgentStudioException.class,
            () -> fileStore.readOrNull("bucket/key"));
        assertEquals(StudioError.OBS_FAILED, thrown.getErrorCode(),
            "readOrNull NoSuchBucket 应抛 OBS_FAILED，不误判为未发布返回 null");
    }

    /** readOrNull: 真实 OBS 故障（非 404，如 500）→ 抛 OBS_FAILED（不掩盖真实故障）。 */
    @Test
    void readOrNull_obsFailure500_throwsObsFailed() {
        when(obsClient.getObject(eq("bucket"), eq("key")))
            .thenThrow(obsException(500, null));
        AgentStudioException thrown = assertThrows(AgentStudioException.class,
            () -> fileStore.readOrNull("bucket/key"));
        assertEquals(StudioError.OBS_FAILED, thrown.getErrorCode(),
            "readOrNull 5xx 应抛 OBS_FAILED，不降级为 null");
    }

    /** readOrNull: 正常读取 → 返回内容。 */
    @Test
    void readOrNull_success_returnsContent() {
        ObsObject obj = new ObsObject();
        obj.setObjectContent(new ByteArrayInputStream("hello".getBytes(StandardCharsets.UTF_8)));
        when(obsClient.getObject(eq("bucket"), eq("key"))).thenReturn(obj);
        assertEquals("hello", fileStore.readOrNull("bucket/key"));
    }

    /** 构造指定 responseCode + errorCode 的 ObsException（SDK 构造器 + 反射设字段）。 */
    private static ObsException obsException(int responseCode, String errorCode) {
        ObsException e = new ObsException("test-" + responseCode);
        ReflectionTestUtils.setField(e, "responseCode", responseCode);
        ReflectionTestUtils.setField(e, "errorCode", errorCode);
        return e;
    }
}
